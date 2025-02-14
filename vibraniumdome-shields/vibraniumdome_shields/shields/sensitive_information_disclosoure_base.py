from abc import abstractmethod
import logging
from typing import List
from uuid import UUID

import spacy
from presidio_analyzer import AnalyzerEngine

from vibraniumdome_shields.shields.model import LLMInteraction, ShieldDeflectionResult, VibraniumShield


class SensitiveShieldDeflectionResult(ShieldDeflectionResult):
    result: dict


class SensitiveInformationDisclosureShieldBase(VibraniumShield):
    _logger = logging.getLogger(__name__)
    _entites = [
        "CREDIT_CARD",
        "PERSON",
        "URL",
        "PHONE_NUMBER",
        "IP_ADDRESS",
        "EMAIL_ADDRESS",
        "DATE_TIME",
        "LOCATION",
        "US_PASSPORT",
        "US_BANK_NUMBER",
        "US_DRIVER_LICENSE",
    ]
    _model_name: str = "en_core_web_lg"

    def __init__(self, shield_name: str):
        super().__init__(shield_name)
        try:
            if not spacy.util.is_package(self._model_name):
                self._logger.info("Start spacy download")
                spacy.cli.download(self._model_name)
            self._logger.info("Spacy is up to date")
        except Exception:
            self._logger.exception("Failed spacy download")

    @abstractmethod
    def _get_message_to_validate(self, llm_interaction: LLMInteraction) -> str:
        pass

    def deflect(self, llm_interaction: LLMInteraction, shield_policy_config: dict, scan_id: UUID, policy: dict) -> List[ShieldDeflectionResult]:
        shield_matches = []
        threshold = shield_policy_config.get("threshold", 0.1)
        try:
            # TODO: consider moving to ctor
            analyzer: AnalyzerEngine = AnalyzerEngine()
            message: str = self._get_message_to_validate(llm_interaction)
            if message:
                analyzer_results = analyzer.analyze(text=message, entities=self._entites, language="en")
                for result in analyzer_results:
                    if result.score > threshold:
                        shield_matches.append(
                            SensitiveShieldDeflectionResult(
                                risk=result.score, result={key: value for key, value in result.to_dict().items() if key != "recognition_metadata"}
                            )
                        )
        except Exception:
            self._logger.exception("Presidio Analyzer error, scan_id: %s", scan_id)

        if len(shield_matches) == 0:
            shield_matches.append(SensitiveShieldDeflectionResult(result={}))

        return shield_matches

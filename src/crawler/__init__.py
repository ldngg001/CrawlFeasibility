"""Crawler modules for CrawlFeasibility"""
from .basic_checker import BasicChecker
from .tech_stack import TechStackChecker
from .anti_spider import AntiSpiderChecker
from .assessment import Assessor

__all__ = ["BasicChecker", "TechStackChecker", "AntiSpiderChecker", "Assessor"]

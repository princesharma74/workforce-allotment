from enum import Enum

class ProjectStatus(str, Enum):
    CONFIRMED = "Confirmed"
    DRAFT = "Draft"
    BACKLOG = "Backlog"

class DesignType(str, Enum):
    HIERARCHICAL = "Hierarchical"
    FLAT = "Flat"

class PackageType(str, Enum):
    FLIPCHIP = "Flipchip"
    WIREBOND = "Wirebond"

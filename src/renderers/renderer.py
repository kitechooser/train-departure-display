from .rail_renderer import RailRenderer
from .tfl_renderer import TflRenderer

def create_renderer(font, fontBold, fontBoldTall, fontBoldLarge, config, mode):
    """Factory function to create the appropriate renderer based on mode"""
    if mode == "tfl":
        return TflRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)
    else:
        return RailRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)

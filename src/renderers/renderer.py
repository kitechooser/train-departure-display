from .rail_renderer import RailRenderer
from .tfl_renderer import TflRenderer

def create_renderer(font, fontBold, fontBoldTall, fontBoldLarge, config, mode, announcer=None):
    """Factory function to create the appropriate renderer based on mode"""
    if mode == "tfl":
        renderer = TflRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)
        if announcer:
            renderer.announcer = announcer
        return renderer
    else:
        renderer = RailRenderer(font, fontBold, fontBoldTall, fontBoldLarge, config)
        if announcer:
            renderer.announcer = announcer
        return renderer

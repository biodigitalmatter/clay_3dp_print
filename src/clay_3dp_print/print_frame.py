from dataclasses import dataclass

import compas.geometry
from compas.tolerance import TOL


@dataclass
class PrintFrame(compas.geometry.Frame):
    """Frame and extrusion value"""

    def __init__(self, frame: compas.geometry.Frame, extrusion_factor: float):
        super().__init__(
            frame.point, xaxis=frame.xaxis, yaxis=frame.yaxis, name=frame.name
        )
        self._extrusion_factor: float = extrusion_factor

    DATASCHEMA = {
        "type": "object",
        "properties": {
            "point": compas.geometry.Point.DATASCHEMA,
            "xaxis": compas.geometry.Vector.DATASCHEMA,
            "yaxis": compas.geometry.Vector.DATASCHEMA,
            "extrusion_factor": "number",
        },
        "required": ["point", "xaxis", "yaxis", "extrusion_factor"],
    }

    @property
    def __data__(self):
        return super().__data__ | {"extrusion_factor": self.extrusion_factor}

    @property
    def extrusion_factor(self) -> float:
        return float(self._extrusion_factor)

    @extrusion_factor.setter
    def extrusion_factor(self, value):
        self._extrusion_factor = value

    def is_travel(self) -> bool:
        if not isinstance(self.extrusion_factor, bool):
            return TOL.is_close(self.extrusion_factor, 0)
        # TODO: Clean this up when I only set numbers not bools
        return bool(self.extrusion_factor)

    def translate_frame_in_local_Z(self, signed_distance: float) -> None:
        """Translates along local Z axis in place."""
        v = self.normal.copy()
        v.scale(signed_distance)
        self.point.translate(v)

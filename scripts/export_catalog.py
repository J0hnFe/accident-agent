"""Exporta desde el codigo el catalogo de valores que acepta `search_accidents` (tarea 3.7).

Uso: uv run python scripts/export_catalog.py > docs/evidencias/func_3.7_catalogo_valores.md
"""

from collections import defaultdict
from collections.abc import Mapping
from enum import StrEnum

from accident_agent.domain import catalogs
from accident_agent.graph.repository import GroupBy
from accident_agent.tools.accident_search import SearchMode

FIELDS: dict[str, tuple[str, Mapping[str, StrEnum]]] = {
    "province": ("Provincia", catalogs.PROVINCES),
    "accident_type": ("Tipo de siniestro", catalogs.ACCIDENT_TYPES),
    "cause": ("Causa probable", catalogs.CAUSES),
    "vehicle_type": ("Tipo de vehiculo", catalogs.VEHICLE_TYPES),
    "weather": ("Clima", catalogs.WEATHERS),
    "surface": ("Superficie", catalogs.SURFACES),
    "lighting": ("Iluminacion", catalogs.LIGHTINGS),
}


def main() -> None:
    print("# Catalogo de valores de busqueda")
    print()
    print("Generado desde el codigo con `uv run python scripts/export_catalog.py`.")
    print("Fuente: `src/accident_agent/domain/catalogs.py` y `tools/accident_search.py`.")
    print("Las mayusculas y las tildes no importan: `Pichincha`, `PICHINCHA` y `pichincha`")
    print("son el mismo valor. Un valor desconocido se rechaza con sugerencias.")
    for field, (title, lookup) in FIELDS.items():
        variants: dict[str, list[str]] = defaultdict(list)
        for key, member in lookup.items():
            if key and key not in {
                member.value.casefold(),
                member.value.replace("_", " ").casefold(),
            }:
                variants[member.value].append(key)
        print()
        print(f"## {title} (`{field}`)")
        print()
        print("| Valor | Texto legible | Otras escrituras aceptadas |")
        print("| --- | --- | --- |")
        for member in type(next(iter(lookup.values()))):
            extra = ", ".join(f"`{v}`" for v in sorted(variants[member.value])) or "-"
            # Las provincias son nombres propios: su valor ya es el texto legible.
            label = member.value if field == "province" else catalogs.display_label(member.value)
            print(f"| `{member.value}` | {label} | {extra} |")
    print()
    print("## Modos (`mode`) y agrupaciones (`group_by`)")
    print()
    print(f"- `mode`: {', '.join(f'`{m.value}`' for m in SearchMode)}.")
    groups = ", ".join(f"`{g.value}`" for g in GroupBy)
    print(f"- `group_by` (obligatorio con `mode=stats`): {groups}.")
    print("- `road`: codigo de via (`E35`, `E45`, `E15`) o parte del nombre (`Via a la Costa`).")
    print("- `canton`: nombre del canton (`Quito`, `Ruminahui`); sin catalogo cerrado.")


if __name__ == "__main__":
    main()

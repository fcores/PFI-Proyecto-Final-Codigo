"""Capa de servicio para calculo de dosis y excedente relativo."""

import logging

from backend.ml.dosis import calcular_dosis_mg, resolver_presentaciones
from backend.ml.regimenes import calcular_excedente_relativo, farmacos_regimen

logger = logging.getLogger(__name__)


class DosisService:
    """Calcula dosis de referencia y excedente usando el catalogo de medicamentos."""

    def __init__(self, medication_repo) -> None:
        """Inicializa el servicio con el repositorio de medicamentos."""
        try:
            self._medication_repo = medication_repo
        except Exception as exc:
            logger.error("Error al inicializar DosisService: %s", exc, exc_info=True)
            raise

    def _presentaciones_de_farmaco(self, farmaco):
        """Obtiene presentaciones del catalogo como lista de dicts para dosis.py."""
        try:
            meds = self._medication_repo.find_by_monodroga(farmaco)
            presentaciones = []
            for med in meds:
                presentaciones.append(
                    {
                        "potencia_mg": med.potencia_mg,
                        "precio": med.precio,
                        "ean": med.ean,
                        "via": med.via_administracion or "",
                    }
                )
            return presentaciones
        except Exception as exc:
            logger.error(
                "Error al obtener presentaciones de %s: %s",
                farmaco,
                exc,
                exc_info=True,
            )
            raise

    def dosis_referencia_regimen(self, id_regimen, bsa, peso_kg):
        """Devuelve la lista de dosis de referencia por farmaco del regimen."""
        try:
            resultado = []
            for farmaco in farmacos_regimen(id_regimen):
                dosis = calcular_dosis_mg(farmaco, bsa, peso_kg, id_regimen)
                resultado.append({"monodroga": farmaco, "dosis_mg": round(dosis, 2)})
            return resultado
        except Exception as exc:
            logger.error(
                "Error al calcular dosis de referencia de %s: %s",
                id_regimen,
                exc,
                exc_info=True,
            )
            raise

    def costear_regimen(self, id_regimen, bsa, peso_kg):
        """Calcula el costo estimado del regimen a partir del catalogo.

        Devuelve (lista_costos, costo_total). Si un farmaco no tiene
        presentaciones en catalogo, su costo queda en None y no suma al total.
        """
        try:
            from backend.models.prescription import CostoFarmaco

            lista = []
            total = 0.0
            hay_precio = False

            for farmaco in farmacos_regimen(id_regimen):
                dosis = calcular_dosis_mg(farmaco, bsa, peso_kg, id_regimen)
                presentaciones = self._presentaciones_de_farmaco(farmaco)
                if presentaciones:
                    resolucion = resolver_presentaciones(dosis, farmaco, presentaciones)
                    costo = resolucion.get("costo", 0)
                    n_pres = len(resolucion.get("presentaciones", []))
                    if costo is not None and costo > 0:
                        hay_precio = True
                        total += costo
                    lista.append(
                        CostoFarmaco(
                            monodroga=farmaco,
                            dosis_mg=round(dosis, 2),
                            costo=round(costo, 2) if costo else None,
                            presentaciones_usadas=n_pres,
                        )
                    )
                else:
                    lista.append(
                        CostoFarmaco(
                            monodroga=farmaco,
                            dosis_mg=round(dosis, 2),
                            costo=None,
                            presentaciones_usadas=0,
                        )
                    )

            costo_total = round(total, 2) if hay_precio else None
            return lista, costo_total
        except Exception as exc:
            logger.error("Error al costear regimen %s: %s", id_regimen, exc, exc_info=True)
            raise

    def calcular_excedente(self, id_regimen, dosis_por_farmaco, bsa, peso_kg):
        """Calcula excedente relativo a partir de las dosis prescritas.

        Si no hay presentaciones en catalogo, estima excedente como
        (dosis_prescrita - dosis_referencia) / dosis_referencia cuando
        la prescrita supera la de referencia; si no, 0.
        """
        try:
            if not dosis_por_farmaco:
                return 0.0

            excedente_total = 0.0
            requerida_total = 0.0

            for item in dosis_por_farmaco:
                if hasattr(item, "monodroga"):
                    farmaco = item.monodroga
                    dosis_prescrita = float(item.dosis_mg)
                else:
                    farmaco = item["monodroga"]
                    dosis_prescrita = float(item["dosis_mg"])

                dosis_ref = calcular_dosis_mg(farmaco, bsa, peso_kg, id_regimen)
                requerida_total += max(dosis_ref, dosis_prescrita, 0.0)

                presentaciones = self._presentaciones_de_farmaco(farmaco)
                if presentaciones:
                    resolucion = resolver_presentaciones(
                        dosis_prescrita,
                        farmaco,
                        presentaciones,
                    )
                    excedente_total += resolucion.get("excedente_mg", 0.0)
                else:
                    if dosis_ref > 0 and dosis_prescrita > dosis_ref:
                        excedente_total += dosis_prescrita - dosis_ref

            return calcular_excedente_relativo(excedente_total, requerida_total)
        except Exception as exc:
            logger.error("Error al calcular excedente relativo: %s", exc, exc_info=True)
            raise

"""
Capa de escritura hacia Oracle legacy (RNIENTREVISTA) — ETAPA A del strangler-fig.

DRY-RUN por defecto en todo punto. Ninguna función de este paquete abre una
conexión a Oracle salvo que se pase `confirmar=True` de forma explícita, y aun
así el destino debe elegirse a mano (local/produccion). Diseño y racional en
docs/oracle-legacy/diseno_etapa_a_escritura.md.
"""

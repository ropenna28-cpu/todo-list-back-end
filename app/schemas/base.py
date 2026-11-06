from datetime import datetime, timezone
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

def _garantir_utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)

DataHoraUTC = Annotated[datetime, AfterValidator(_garantir_utc)]

class EsquemaDeEntrada(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class EsquemaDeSaida(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

from pydantic import BaseModel, Field


class SettingWrite(BaseModel):
    value: dict | list | str | int | float | bool | None


class SettingResponse(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,119}$")
    value: object

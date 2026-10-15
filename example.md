# PlantUML под курсором

Поставь курсор на строку внутри любого блока и нажми Ctrl+Option+P.
Документ сохранится автоматически; локальный PNG откроется в Preview.

## Диаграмма с полной обёрткой

```puml
@startuml
actor Пользователь as User
participant Zed
participant PlantUML
User -> Zed: Ctrl+Option+P
Zed -> PlantUML: Блок под курсором оавшоавоваш
PlantUML --> User: Локальный PNG в Preview
@enduml
```

## Можно и без @startuml / @enduml

```plantuml
Alice -> Bob: Привет!
Bob --> Alice: Работает локально
```

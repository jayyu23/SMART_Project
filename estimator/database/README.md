# SMART IPCL Database Structure

*Updated 2021-03-03 by Jay Yu*

*Shensilicon Semiconductors*

## Overview
The SMART database is known as the Intelligent Primitive Component Library (IPCL). This contains all the most basic components necessary to build up a microchip, including but not limited to:
- Adders
- Multipliers
- Registers

-------

## Structure

|             | ID                          | Component             | Action           | Arguments                                                    | DefaultValues                                                | Energy/Area/Cycle Function                                   | Comments                 |
| ----------- | --------------------------- | --------------------- | ---------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------ |
| Data Type   | INT                         | STR                   | STR              | STR                                                          | STR                                                          | STR                                                          | STR                      |
| Description | Primary Key, Auto-Increment | Name of the component | Component action | **Python array** of relevant arguments for the actions to calculate Energy/Area/Cycle | **Python array** to instantiate defaults for each item in **Arguments** | **Python code** with a `return` statement indicating the value to be used | Description of the entry |
| Example     | 1                           | register              | read             | `[latency]`                                                  | `[5]`                                                        | See code below for `EnergyFunction` example                  | 1 stage energy           |

```python
# returns dynamic energy pJ
if latency <= 5:
	return 0.009
elif latency == 10:
	return 0.00554
```

## Why User-Defined Python Function in ICPL?

The most significant aspect of the IPCL and the reason why it is referred to as being "intelligent" is the inclusion of Python functions within each database entry in order to calculate the energy, area, clock cycles for each component. Each of these functions is able to use a set of parameters defined in the **Arguments** column of each database, with default values (that may be over-ridden) using user-defined YAML documents noting the larger architecture.

Here are a few reasons for including Python functions in the ICPL to calculate energy/area/cycles:

- Highly customizable, allows for the user to leverage Python logic (such as `if-elif-else`, `for` and other operators) to describe wide variety of circumstances
- Python code is highly readable/editable
- Can leverage Python `eval(str)` function to directly implement, therefore much more succinct program logic

## Database Tables

Each table in the database represents a different configuration. This allows the user to flexibly switch between different sets of primitive components. The SQL used to create each table is as follows:

```sqlite
CREATE TABLE "TableName" (
	"ID"	INTEGER NOT NULL,
	"ComponentName"	TEXT NOT NULL,
	"Action"	TEXT NOT NULL,
	"Arguments"	TEXT NOT NULL DEFAULT '[]',
	"DefaultValues"	TEXT NOT NULL DEFAULT '[]',
	"EnergyFunction"	TEXT,
	"AreaFunction"	TEXT,
	"CycleFunction"	TEXT,
	"Comments"	TEXT,
	PRIMARY KEY("ID" AUTOINCREMENT)
)
```
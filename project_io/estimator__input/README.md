# SMART Estimator Input Files + Mapper Output Files README

*Updated 2021-03-15 by Jay Yu*

*Shensilicon Semiconductors*

## Overview

The SMART system will read input user-defined files in order to create Energy/Area/Cycle Reference Tables and Estimations. These input files are split into three categories:

1. **Architecture file**, a YAML document, containing a description of the entire microchip architecture. 
2. **Operations file**, a YAML document, detailing the operations sequence and operation counts for the architecture. 
3. **Compound Components folder**, containing user-defined compound components, which can be used in the architecture template. Each compound component is represented through a YAML document.

## Architecture File

The architecture file is a high-level overview of the microchip template. Within the `components` list of the architecture file, the user is able to define items of either `component` or `group` type.

- `component` refers to each specific component within the architecture. Components cover two categories: primitive components and compound components, which are discussed more below.
- `group` refers to a grouping of multiple components. *This is used for ease of input and reading only,* since internally the SMART system will extract the individual components inside the group

### Primitive Components

- Most basic and low level components that make up all architecture (eg. adder, register)
- Attributes and actions are defined in the `intelligent_primitive_component_library.db` or IPCL SQLite database file as under the `data` folder
- The way in which IPCL is defined is described in the `README.md` file under that directory

### Compound Components

- These are higher-level components that are defined as combinations of different components
- For example, a MAC unit consists of the primitive components of a multiplier, adder, and register (accumulator)
- See **Compound Components** section to see how these are defined

### Example

```yaml
architecture:
  name: simple_architecture
  version: 0.3
  components:
    - type: group
      name: compound_components
      components: # Defined in Compound Components Folder
        - {type: component, name: pe, class: processing_element}
    - type: group
      name: primitive_components # Defined in Intelligent Primitive Component Library
      components:
        - {type: component, name: simple_register, class: register}
        - {type: component, name: simple_int_adder, class: adder}
```

## Operations File

The operations file describes the different operations that each component will conduct, as well as the number of times that the component will conduct this action. The user can define operation arguments within this space. Operations can be of type **serial**, **parallel**, or **loop** (a container containing a sub-list of loop operations). In the case of serial/parallel operations, the specific actions are noted using Pythonic method notation, `object.method(arg1 = v1, arg2 = v2)`.

### Loops

**Note: Please use loops sparingly.** *Use the `operation-times` parameter instead to repeat identical actions.*  This is because the SMART system needs to internally *expand* each loop, producing a "flattened" operations list that only contain serial and parallel operations. This "flattening" process takes up a lot of system memory, and can greatly reduce operating efficiency. 

As a general rule of thumb, **only use loops when operations depend on the loop variables, or when arguments change each iteration during runtime.** Loops may also be nested.

In the case of a loop, there are several parameters that may be modified:

- `loop-param`: this is a dictionary with `start` `stop` and `step` (default step = 1) keys, that describe the general loop shape

- `loop-variable`: this declares a loop variable, which can be used inside the loop body. The value of the loop variable will change as the loop completes each iteration. The loop variable must begin with a "$" sign.

  > Note: because of the way the program is structured, nested loop variables must each have a completely distinct variable names that **are not subsets of each other**. This means that you cannot have a loop variable called `$myVar` and another called `$myVarAsWell` (since it contains the `'myVar' `phrase). However, you *can* have another variable called `$myVaR`.

- `loop-body`: this is a list with the iterated actions inside the loop.

### Example

```yaml
operations:
  - type: serial
    operation: pe.pe_process()
    operation-times: 20

  - type: serial
    operation: intmac.idle()
    operation-times: 3

  - type: parallel # In parallel, count the action with the maximum clock
    operations:
      - simple_register.read(latency = 0.5)
      - intmac.mac(latency = 0.5)
    operation-times: 10

  - type: pipeline
    stages:
      - operation: psram.read()
        count: 64
      - operation: data_sram.read()
        count: 8 # Count is the total amount of times the operation is performed
        offset: 8 # Offset refers to gap since last stage. Default 1. If 0, parallel to previous stage
        stride: 1 # There is (stride - 1) gap between each operation
      - operation: pe.mac()
        count: 64
      - operation: data_sram.write()
        count: 8

  - type: parallel # In parallel, count the action with the maximum clock
    operations:
      - simple_register.read(latency = 0.5)
      - simple_int_adder.add(latency = 0.5)
    operation-times: 10

```



## Compound Components Folder

The compound components folder consists of all of the user-defined compound components. Inside the compound components folder, there is a special file that describes the order in which the compound components files are initiated in. This is the `_instance_order.yaml` file. Without this file, the files will be instantiated in alphabetical order.

Each YAML in this compound components folder describes one compound component. This compound component may be constructed using either **primitive components** (as stored in the SQLite database) or **compound components** that have been previously defined. In each compound component, there are the following sections:

### Subcomponents

This section describes the hardware components (primitive or previously defined compound) that form up this new compound component.

### Operations

Operations of compound components are defined within this section. Each operation contains two parts, a **name** and a **definition**. The latter contains a list of the steps of the operation. A `serial` step will be carried out in sequence, whereas a `parallel` step will be carried out in parallel. These operation definitions are the same as those found in the operations file. For every subcomponent in a compound component, if a specific operation is not defined, it will *by default* interpret this subcomponent as `idle`

### Examples

#### Example Instance Order File

```yaml
# Describes the order in which compound component files are initiated in
# Is a simple list
- mac.yaml
- pe.yaml
```

#### Example Compound Component

```yaml
compound_component:
  name: mac
  arguments: {latency: 5}
  subcomponents:
    - {class: multiplier, name: mult,        arguments: {latency: latency}}
    - {class: adder,      name: add,         arguments: {latency: latency}}
    - {class: register,   name: accumulator, arguments: {latency: latency}}

  operations:
    - name: mac
      definition:
        - type: serial
          operation: mult.multiply()
        - type: serial
          operation: add.add()
        - type: serial
          operation: accumulator.write()
```




# ecmc-ioc-generator

A Python tool for scanning the EtherCAT bus and automatically generating an ecmc-compatible EPICS IOC startup script.

This tool is designed to work with the [ecmc](https://github.com/paulscherrerinstitute/ecmc) (EtherCAT Motion Control) framework and its configuration tool [ecmccfg](https://github.com/paulscherrerinstitute/ecmccfg).

## Features

- **Automated Scanning**: Polls the EtherCAT bus using the `ethercat` command.
- **Facility Support**: Generates site-specific headers and footers for **ESS** and **PSI**.
- **Axis Templates**: Detects common Beckhoff motion terminals (EL7xxx, AX5xxx) and generates placeholder axis configurations.
- **Robust Indexing**: Extracts absolute bus indices to ensure accurate hardware mapping even with unknown devices.
- **Flexible Output**: Supports printing to terminal (stdout) or writing directly to a file.

## Compatibility

This tool supports both **Python 2.7** and **Python 3.x** to ensure compatibility with legacy IOC machines.

## Installation

You can install the tool directly from the repository:

```bash
git clone https://github.com/your-repo/ecmc-ioc-generator.git
cd ecmc-ioc-generator
pip install .
```

## Usage

### Basic Scan (Live Bus)
Run the script on an EtherCAT master machine:

```bash
ecmc-ioc-gen
```

### From Saved Output (Piped)
If you are not on a master machine, you can pipe a saved `ethercat slaves` output into the tool:

```bash
cat slaves.txt | ecmc-ioc-gen
```

### Facility Selection
Toggle between ESS and PSI output standards (default is ESS):

```bash
ecmc-ioc-gen --facility PSI
```

### Write to File
Generate a startup script directly to a file:

```bash
ecmc-ioc-gen -o st.cmd
```

### Verbose Mode
Include hardware descriptions and axis details in the output:

```bash
ecmc-ioc-gen --verbose
```

## Configuration

The tool recognizes a variety of Beckhoff modules. Motion terminals currently supported for placeholder generation include:
- Stepper Terminals: EL7031, EL7037, EL7041, EL7047
- Servo Terminals: EL7201, EL7211, EL7221
- Digital Servo Drives: AX5101, AX5103, AX5203

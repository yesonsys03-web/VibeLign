# VibeLign — Repository Structure

vibelign/

cli/
analysis/
engine/
patch/
preview/
simulator/
ui/
recipes/
examples/
docs/

Important rule:

CLI contains commands only.
All logic must live outside CLI so both CLI and GUI reuse the same engine.
DOXYGEN=doxygen
PLANTUML=~/Documents/util_scripts/lib/plantuml.jar
IMAGE_PATH=docs/images

TARGETS=flow2xml.py

.PHONY:
png: $(TARGETS)
	java -jar $(PLANTUML) -o $(IMAGE_PATH) $<

.PHONY:
docs: png
	$(DOXYGEN)

DOXYGEN=doxygen
PLANTUML=~/Documents/util_scripts/lib/plantuml.jar
IMAGE_PATH=docs/images
SVG_PATH=docs/svg

TARGETS=flow2xml.py

.PHONY:
png: $(TARGETS)
	java -jar $(PLANTUML) -o $(IMAGE_PATH) $<

.PHONY:
svg: $(TARGETS)
	java -jar $(PLANTUML) -o $(SVG_PATH) -svg $<

.PHONY:
docs: png
	$(DOXYGEN)

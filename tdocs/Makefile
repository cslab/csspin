PDFs=$(addsuffix .pdf, $(basename $(wildcard *.md)))

%.pdf : %.md
	pandoc $< -o $@ --variable colorlinks -V geometry:margin=1.5in

all: $(PDFs)

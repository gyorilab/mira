SPHINXBUILD = python -m sphinx
SOURCEDIR = source
BUILDDIR = build

html:
	$(SPHINXBUILD) -b html -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html

latexpdf:
	$(SPHINXBUILD) -b latex -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/latex
	make -C $(BUILDDIR)/latex all-pdf


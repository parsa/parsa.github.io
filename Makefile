all:
	jekyll build
clean:
	rm -rf _site .sass-cache
serve:
	jekyll serve

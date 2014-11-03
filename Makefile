test:
	~/thehat/google_appengine/appcfg.py update . -V 2 --oauth2
deploy:
	@echo "With great power comes great responsibility"
	@echo "Are you sure you want to deploy to production server?"
	@echo "Use deploy_im_sure target"
deploy_im_sure:
	~/thehat/google_appengine/appcfg.py update . -A "the-hat" -V 3 --oauth2

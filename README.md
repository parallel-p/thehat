# The Hat project

Application URL: [http://the-hat-international.appspot.com/](http://the-hat-international.appspot.com/)

## Localization

Firstly, we need to tag words in templates using {% trans %} {% endtrans %} (i18n extension). More information in [Jinja2 documentation](http://jinja.pocoo.org/docs/extensions/#i18n-extension). Default language is Russian, but for clean templates it will be better to translate them to English. Locales are stored in locale dir. Good example of tagged templates is [index.html](https://github.com/Sibyx/thehat/blob/master/templates/index.html)

Tagged text text (messages) should by extracted by bybabel ([installation](http://webapp-improved.appspot.com/tutorials/i18n.html#get-babel-and-pytz)). For more info how to use bybabel, read article [Internationalization and localization with webapp2](http://webapp-improved.appspot.com/tutorials/i18n.html#extract-and-compile-translations).

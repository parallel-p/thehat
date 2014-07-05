# The Hat project

## Localization
To tag words in templates we use Jinja2 i18n extension and tags {% trans %} & {% endtrans %}. More information in a official [Jinja2 documentation](http://jinja.pocoo.org/docs/extensions/#i18n-extension). Default language is Russian, but for clean templates it will be better to translate them to English. Translations are stored in locale dir. Good example of tagged templates is [index.html](https://github.com/Sibyx/thehat/blob/master/templates/index.html).

Tagged text (messages) can be extracted by the bybabel tool ([installation](http://webapp-improved.appspot.com/tutorials/i18n.html#get-babel-and-pytz)). For more info how to use bybabel, read article [Internationalization and localization with webapp2](http://webapp-improved.appspot.com/tutorials/i18n.html#extract-and-compile-translations).

Cool software for translating and compiling .po catalogs is [PoEdit](http://poedit.net) (Widnows/Mac/Linux)
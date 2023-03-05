echo 'THIS NUKES the arepl_jsonpickle directory! Beware!'
REM exit for safety. User can change this manually
goto end

git clone https://github.com/jsonpickle/jsonpickle.git
REM this requires https://github.com/bmatzelle/gow
rm -rf arepl_jsonpickle
mv jsonpickle/jsonpickle arepl_jsonpickle
sed -i s/__import__('jsonpickle.handlers/__import__('arepl_jsonpickle.handlers/ arepl_jsonpickle/__init__.py

:end
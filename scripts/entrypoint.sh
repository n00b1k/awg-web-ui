#!/bin/sh

# Если первый аргумент "gph", то запускаем генератор пароля
if [ "$1" = "gph" ]; then
    shift
    exec python3 /app/web-ui/generate_password_hash.py "$@"
fi

# Иначе запускаем основной процесс
exec "$@"
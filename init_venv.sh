
venv/bin/python3 --version 2>/dev/null
if [[ $? -ne 0 ]]; then
    virtualenv venv
fi

venv/bin/pip3 install --upgrade -r requirements.txt

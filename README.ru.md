[English](README.md) | **Русский**

# Python Embeddable Manager

Менеджер портативных версий Python для Windows: скачивает **embeddable package** с python.org в выбранную папку и позволяет запускать их без установки в систему.

## Зачем

- Одна папка со всеми нужными версиями (3.10, 3.11, 3.12 и т.д.)
- Не трогает системную установку Python
- Удобно для CI, портативных сборок, тестов под разными версиями
- Можно положить на флешку или в репозиторий (без самих бинарников)

## Требования

- Windows (embeddable пакеты есть только под Windows)
- Любой уже установленный Python 3.x для запуска менеджера (или один раз скачайте один embed и запускайте менеджер им — см. ниже)

Если в консоли вместо русского отображаются кракозябры, выполните один раз: `chcp 65001` или задайте `PYTHONIOENCODING=utf-8`.

## Чистый компьютер без Python

На машине без установленного Python менеджер сам по себе не запустится (`python run.py` и `pyembed` требуют интерпретатора). Нужен **один раз ручной бутстрап**:

1. **Скачайте один embeddable-архив** с python.org, например:
   - 64-bit: https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip  
   - 32-bit: замените в URL `amd64` на `win32`.

2. **Распакуйте** архив в любую папку (например `C:\py\3.12.0`). Внутри должны быть `python.exe` и др.

3. **Скопируйте проект PythonManager** на этот компьютер (папка с `run.py`, `pyembed/` и т.д.).

4. **Запускайте менеджер этим Python:**
   ```bat
   C:\py\3.12.0\python.exe run.py list
   C:\py\3.12.0\python.exe run.py install 3.14.3 --pip
   ```
   Дальше можно ставить остальные версии через менеджер и пользоваться ими как обычно.

5. **(По желанию)** Добавьте в PATH папку с бутстрап-Python или с проектом, чтобы не вводить полный путь каждый раз.

После этого «первая» версия используется только для запуска менеджера; все остальные версии вы уже получаете через `install`.

### Автоматический бутстрап

На чистом компьютере можно **не делать шаги 1–4 вручную**: запустите **`bootstrap.bat`** или **`.\bootstrap.ps1`** из папки проекта. Скрипт:

- проверяет, есть ли в системе Python или уже скачанная версия в `pythons\`;
- если нет — сам скачивает embed **3.12.0** с python.org (64- или 32-bit по системе) в `pythons\3.12.0` и распаковывает;
- затем запускает менеджер с переданными аргументами.

Примеры:
```bat
bootstrap.bat
bootstrap.bat list
bootstrap.bat install 3.14.3 --pip
```
Двойной клик по `bootstrap.bat` откроет меню менеджера (или скачает 3.12.0 при первом запуске, затем меню).

## Установка

Клонируйте репозиторий или скачайте архив, перейдите в папку проекта:

```bash
git clone <url-репозитория> PythonManager
cd PythonManager
pip install -e .
```

Или без установки пакета: `pip install -r requirements.txt` (зависимостей нет, только для совместимости) и запуск `python run.py` из папки проекта. После `pip install -e .` доступна команда **`pyembed`** из любого места (если Scripts в PATH).

## Удобный запуск

Запуск **без аргументов** открывает **интерактивное меню** (скрипт не закрывается):

- Показаны установленные версии (и пометка `[pip]`, если pip установлен)
- **1** — Скачать версию (с опцией установки pip)
- **2** — Удалить версию
- **3** — Pip: установка/список пакетов для выбранной версии
- **4** — Установить pip в уже установленную версию
- **5** — Пакеты (список / установить / удалить)
- **6** — Создать venv (виртуальное окружение)
- **7** — PATH: добавить/убрать версию или убрать дубликаты (Windows)
- **8** — Инфо о версии (путь, pip, размер, PATH)
- **9** — Кэш (список / очистка)
- **10** — Обновить pip в версии
- **11** — Копировать версию в папку (например C:/Python/3.15) и в PATH
- **12** — Выход

В пунктах 2–11 версию можно ввести номером из списка (1, 2, …) или строкой (3.12.0).

Из папки проекта: `pyembed.bat` или `.\pyembed.ps1`. С аргументами — те же команды, что и у `python run.py` (list, install, pip, packages, path, add-pip, uninstall, run, use). Чтобы вызывать из любой папки, добавьте каталог проекта в PATH.

## Использование

Корневая папка для версий по умолчанию: `PythonManager\pythons`. Её можно изменить переменной окружения `PYEMBED_ROOT` или флагом `--root`.

### Все команды (кратко)

| Команда | Описание |
|---------|----------|
| `list` | Установленные версии; `-a` — доступные на python.org |
| `install <версия> [--pip] [-y]` | Скачать и распаковать; `-y` — без подсказки после установки |
| `which [версия]` | Путь к python.exe |
| `path show/add/remove/list/fix-duplicates` | Путь и управление PATH (Windows); fix-duplicates — убрать дубликаты |
| `packages <версия> list/add/remove` | Пакеты (pip) для версии |
| `pip <версия> <аргументы>` | Запуск pip для версии |
| `venv <версия> [имя]` | Создать виртуальное окружение |
| `run <версия> [аргументы]` | Запустить эту версию Python |
| `use <версия>` | Подсказка: как добавить в PATH |
| `default [версия]` | Версия по умолчанию для run/which/path show |
| `verify [версия]` | Проверка целостности установки |
| `info [версия]` | Путь, pip, размер, в PATH |
| `cache list/clear [версия]` | Кэш архивов |
| `upgrade-pip [версия]` | Обновить pip в версии |
| `add-pip <версия>` | Установить pip в уже установленную версию |
| `uninstall <версия> [-y]` | Удалить версию (перед подтверждением показывается размер) |
| `copy <версия> [папка] [--force] [--no-path] [--dry-run]` | Скопировать версию в папку и в PATH (Windows); `--dry-run` — только показать план |
| `doctor [--fix]` | Проверка: python.org, диск, целостность версий, PATH (дубликаты и несуществующие каталоги); --fix — исправить |
| `ide [версия] [--json]` | Путь для Cursor/VS Code (python.defaultInterpreterPath); --json — фрагмент для settings.json |

```bash
# Показать установленные версии
pyembed.bat list
# или: python run.py list

# Показать доступные версии на python.org
pyembed.bat list -a

# Скачать и распаковать Python 3.12.0
pyembed.bat install 3.12.0

# Скачать с установкой pip в эту версию
pyembed.bat install 3.12.0 --pip
# Без подсказки после установки (для CI/скриптов)
pyembed.bat install 3.12.0 --pip -y

# Путь к python.exe и управление PATH (Windows)
pyembed.bat which 3.12.0         # путь к python.exe (удобно для скриптов и CI)
pyembed.bat which 3.12.0 -c      # путь и копирование в буфер обмена
pyembed.bat path show 3.12.0
pyembed.bat path show -c         # путь по умолчанию и копировать в буфер
pyembed.bat path add 3.12.0      # добавить в PATH пользователя
pyembed.bat path remove 3.12.0   # убрать из PATH
pyembed.bat path list            # какие версии из этого корня в PATH
pyembed.bat path fix-duplicates  # убрать дубликаты записей в PATH

# Скопировать версию в папку (например C:/Python/3.15) и добавить в PATH
pyembed.bat copy 3.15.0                    # по умолчанию C:/Python/3.15.0
pyembed.bat copy 3.15.0 C:/Python/3.15     # указать папку
pyembed.bat copy 3.15.0 --force            # перезаписать, если папка существует
pyembed.bat copy 3.15.0 C:/Python/3.15 --no-path  # не добавлять в PATH

# Управление пакетами (pip) для версии
pyembed.bat packages 3.12.0 list
pyembed.bat packages 3.12.0 add requests
pyembed.bat packages 3.12.0 remove requests

# Виртуальное окружение (venv) от выбранной версии
pyembed.bat venv 3.12.0
pyembed.bat venv 3.12.0 myenv

# Запустить эту версию
pyembed.bat run 3.12.0 -c "print(1)"
pyembed.bat run 3.12.0 script.py

# Версия по умолчанию (для run/path show без указания версии)
pyembed.bat default              # показать
pyembed.bat default 3.12.0       # задать
pyembed.bat run -c "print(1)"    # использует версию по умолчанию

# Подсказка: как добавить версию в PATH (без изменения реестра)
pyembed.bat use 3.12.0

# Удалить версию (с подтверждением; -y — без)
pyembed.bat uninstall 3.12.0
pyembed.bat uninstall 3.12.0 -y

# Проверить целостность установленной версии
pyembed.bat verify 3.12.0

# Информация о версии (путь, pip, размер, в PATH)
pyembed.bat info 3.12.0
pyembed.bat info                  # версия по умолчанию

# Кэш скачанных архивов
pyembed.bat cache list            # показать файлы в кэше
pyembed.bat cache clear           # очистить весь кэш
pyembed.bat cache clear 3.12.0    # очистить кэш только для 3.12.0

# Обновить pip в установленной версии
pyembed.bat upgrade-pip 3.12.0
pyembed.bat upgrade-pip            # версия по умолчанию

# Установить pip в уже установленную версию (без переустановки)
pyembed.bat add-pip 3.12.0

# Pip для выбранной версии (нужен install --pip или add-pip)
pyembed.bat pip 3.12.0 install requests
pyembed.bat pip 3.12.0 list
pyembed.bat pip 3.12.0 uninstall requests
```

Пример вывода `use`:

```
Добавьте в PATH для использования этой версии:
  set PATH=T:\Projects\PythonManager\pythons\3.12.0;%PATH%
Или запускайте напрямую: T:\Projects\PythonManager\pythons\3.12.0\python.exe
```

## FAQ

- **Нет сети / таймаут при скачивании.** Убедитесь, что python.org доступен. При необходимости скачайте embed-архив вручную и распакуйте в `pythons/<версия>/` (например `pythons/3.12.0/`), затем при необходимости установите pip: `pyembed add-pip 3.12.0`.
- **Нужна ARM64.** Укажите архитектуру: `pyembed install 3.12.0 --arch arm64` (если на python.org есть сборка для arm64).
- **Где хранится кэш?** В папке `pythons/.cache/` (или `PYEMBED_ROOT/.cache/`). Команды: `pyembed cache list`, `pyembed cache clear [версия]`.
- **Как полностью удалить менеджер?** Удалите папку проекта. Если добавляли версии в PATH через `path add`, удалите соответствующие строки из переменной PATH пользователя (Параметры → Переменные среды → Path) или выполните `pyembed path remove <путь_к_каталогу_версии>` для каждой версии.
- **Кракозябры в консоли.** Выполните `chcp 65001` или задайте `PYTHONIOENCODING=utf-8`.

## Кэш и сборка exe

- **Кэш архивов:** скачанные zip хранятся в `pythons/.cache/` и переиспользуются при повторной установке той же версии (и архитектуры). Команды: `pyembed cache list`, `pyembed cache clear`. Вручную — очистка папки `.cache`.
- **Сборка одного exe:** `pip install pyinstaller`, затем из корня проекта:
  ```bat
  python scripts/build_exe.py
  ```
  Или вручную: `pyinstaller --onefile --name pyembed --paths . run.py`. Готовый `pyembed.exe` будет в `dist/`. Подходит для машин без установленного Python (наряду с bootstrap.ps1).

## Структура после установки

```
PythonManager/
  pythons/
    .cache/           # кэш скачанных zip (опционально)
    3.12.0/
      python.exe
      python312.dll
      python312._pth
      ...
    3.11.5/
      ...
  pyembed/
  run.py
  requirements.txt
```

## Архитектура

По умолчанию ставится пакет под текущую архитектуру (amd64 / win32 / arm64). Явно задать можно так:

```bash
python run.py install 3.12.0 --arch amd64
```

## Запуск как модуля

```bash
python -m pyembed list
python -m pyembed install 3.12.0 --pip
```

## Python vs Rust

Менеджер написан на **Python**, потому что:

- Быстрее написать и править
- Целевая аудитория уже имеет или скоро получит Python
- Удобно использовать `zipfile`, `urllib`, парсинг HTML

**Rust** имел бы смысл, если нужен один исполняемый файл без зависимости от установленного Python (например, раздавать один .exe на «голую» Windows). Тогда менеджер можно было бы распространять как единственный бинарник и использовать для бутстрапа первой версии. При желании позже можно портировать логику на Rust.

## Разработка и CI

- Тесты: `pip install -e ".[dev]"`, затем `pytest tests/ -v`.
- Линтер: `ruff check pyembed`.
- Типы: `pyright` в режиме strict (в `pyrightconfig.json` задано `typeCheckingMode: "strict"`).
- В репозитории можно включить GitHub Actions (см. `.github/workflows/ci.yml`) для прогона тестов на Windows при push/PR.

### Примеры использования в CI

**GitHub Actions** — установка версии через pyembed и запуск тестов:

```yaml
- name: Install Python via pyembed
  run: |
    pip install -e .
    pyembed install 3.12.0 --pip
    pyembed default 3.12.0
- name: Run tests
  run: pyembed run -m pytest tests/ -v
```

**GitLab CI** — то же самое:

```yaml
test:
  script:
    - pip install -e .
    - pyembed install 3.12.0 --pip
    - pyembed default 3.12.0
    - pyembed run -m pytest tests/ -v
```

Корень установки можно задать переменной `PYEMBED_ROOT` (например, в CI — каталог в кэше).

## Интеграция с Cursor / VS Code

Cursor и VS Code используют интерпретатор Python из настройки **`python.defaultInterpreterPath`** или из выбора «Python: Select Interpreter». Чтобы использовать версию, установленную через pyembed:

### Способ 1: путь вручную

Узнайте путь к нужной версии и укажите его в настройках:

```bash
pyembed which 3.12.0
# или версия по умолчанию:
pyembed which
```

Скопируйте вывод (или `pyembed which 3.12.0 -c` — путь попадёт в буфер обмена). В Cursor/VS Code: **Ctrl+Shift+P** → «Python: Select Interpreter» → «Enter interpreter path...» → вставьте путь к `python.exe`.

### Способ 2: команда ide и settings.json

Команда **`pyembed ide`** выводит путь и подсказку; с флагом **`--json`** — готовый фрагмент для `settings.json`:

```bash
pyembed ide 3.12.0
# Только JSON (для вставки в .vscode/settings.json):
pyembed ide 3.12.0 --json
```

В корне проекта создайте или дополните `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "T:\\Projects\\PythonManager\\pythons\\3.12.0\\python.exe"
}
```

Путь подставьте из вывода `pyembed which 3.12.0` или `pyembed ide 3.12.0 --json`.

### Способ 3: через PATH

Если добавить нужную версию в PATH (`pyembed path add 3.12.0`), Cursor при сканировании окружения может показать её в списке интерпретаторов. Тогда достаточно выбрать её в «Python: Select Interpreter».

### Несколько версий в одном проекте

Для разных папок можно задать свой интерпретатор в workspace-настройках (`.vscode/settings.json` в проекте), указав путь к `python.exe` из pyembed для нужной версии.

## Разработка

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check pyembed scripts
```

## Лицензия

MIT. См. [LICENSE](LICENSE).

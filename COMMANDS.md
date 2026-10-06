# Команды

Всё выполняется в WSL, в папке проекта `~/reflection`, с активным окружением.

Как написать тест для нового модуля, описано в `GUIDE.md`.

## Каждый раз, когда открываешь консоль

```bash
conda activate reflection
cd ~/reflection
```

В начале строки должно быть `(reflection)`.

## Тесты и симуляция

```bash
python -m pytest tests -q                    # all tests (model, generator, UVM)
python -m pytest tests -v                    # same, one line per test
python -m pytest tests/test_uvm.py -q        # only the UVM bench
python -m pytest tests -k wrapper -q         # only tests with "wrapper" in the name
python -m pytest tests -x                    # stop at the first failure
```

```bash
python -m Engine.Run mac_q16                         # UVM bench for one module
python -m Engine.Run pe_mac_wrapper
python -m Engine.Run mac_q16 PIPELINE_STAGES=7       # override a TB parameter
python -m Engine.Run pe_mac_wrapper seed=1234        # repeat a run with a given seed
```

Seed каждого прогона печатается в логе строкой `seed N`. Если прогон упал, этот номер воспроизводит его один в один.

## Покрытие

```bash
python -m Engine.Cover pe_mac_wrapper               # coverage on the model only, no simulator (fast)
python -m Engine.Cover pe_mac_wrapper seed=7
python -m Engine.Cover pe_mac_wrapper seeds=50      # seeds 1..50 merged
python -m Engine.Run pe_mac_wrapper seeds=20        # real simulation on 20 seeds, coverage merged
```

`Engine.Cover` — для настройки `Scenario.py` и `Coverage.py`: поправил, запустил, посмотрел дыры. Симулятор не нужен, занимает доли секунды. `Engine.Run` печатает тот же отчёт в конце настоящего прогона и сохраняет его в `sim_build/<модуль>/coverage.json` (`coverage_merged.json` для `seeds=N`).

В отчёте строка `MISSING` перечисляет корзины, в которые не попали (или попали меньше `at_least` раз).

## Новая версия из архива

```bash
./update.sh /mnt/c/Users/INTEL/Downloads/reflection_stepN.zip
git diff                                     # look at what changed
git add -A
git commit -m "stepN: short description"
git push github v2
```

`update.sh` сам проверяет, что у тебя нет незакоммиченных изменений, распаковывает архив поверх проекта, показывает файлы, которых нет в новой версии (их удалить руками, если они убраны), и запускает тесты. Коммит он не делает.

Если скрипт не запускается: `chmod +x update.sh`.

Скрипт обновляет тот проект, в папке которого ты стоишь, а не тот, где лежит сам. Вне git-репозитория проекта он откажется работать. Поэтому его можно поставить как команду, доступную из окружения:

```bash
cp update.sh $CONDA_PREFIX/bin/rfl-update && chmod +x $CONDA_PREFIX/bin/rfl-update
cd ~/reflection && rfl-update /mnt/c/Users/INTEL/Downloads/reflection_stepN.zip
```

## Git: каждый день

```bash
git status                     # what changed, what is staged
git diff                       # changes not yet staged
git diff --staged              # changes that will go into the commit
git add -A                     # stage everything
git add path/to/file           # stage one file
git commit -m "message"        # commit
git push github v2             # send the v2 branch to GitHub
git log --oneline -15          # last 15 commits
git log --oneline -- Engine/   # commits that touched Engine/
git show HEAD                  # what the last commit changed
```

## Git: откатить

```bash
git restore path/to/file       # drop uncommitted changes in one file
git restore .                  # drop ALL uncommitted changes (careful)
git restore --staged file      # unstage, keep the change in the file
git commit --amend             # fix the last commit (message or forgotten file), before push
git revert <hash>              # undo a pushed commit with a new commit
```

## Git: ветки

```bash
git branch                     # list branches, * = current
git switch v2                  # go to a branch
git switch master              # old version (v1)
git switch -c try-something    # new branch from where you are
git merge try-something        # bring a finished branch into the current one
```

## Копия на диске D

`D:\FPGA\reflection` — вторая копия, она тянет с GitHub. Коммитить в ней не надо, только обновлять:

```bash
cd /mnt/d/FPGA/reflection
git switch v2                  # once: show v2 files in the Windows folder
git pull origin v2             # after later pushes: update the files
```

## WSL и пути

```bash
explorer.exe .                 # open the current folder in Windows Explorer
code .                         # open in VS Code (needs the WSL extension)
cd /mnt/d/FPGA                 # Windows D:\FPGA from WSL
cp /mnt/c/Users/INTEL/Downloads/file.zip ~/     # take a file from Windows downloads
```

Из Windows папку проекта видно по адресу `\\wsl$\Ubuntu\home\intel\reflection`. Работай с проектом в `~/`, а не на `/mnt/d`: через `/mnt` всё в разы медленнее.

## Окружение и пакеты

```bash
python -m pip install -r requirements.txt    # after an update that changed requirements.txt
python -m pip list | grep -i -E "cocotb|pyuvm|pyslang|pytest"
conda env list                               # all conda environments
iverilog -V                                  # Icarus version
```

## Уборка

```bash
rm -rf sim_build .pytest_cache               # build leftovers, recreated on the next run
find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

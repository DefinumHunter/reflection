# Запуск на университетском сервере (Xcelium)

Заметки на 2026-10-06. Ничего из этого ещё не делалось, это план и то, что удалось выяснить.

## Зачем

Локально всё работает на Icarus. Сервер нужен для того, чего Icarus не умеет:

- SVA (`assert property`) — требование кафедры;
- формальная проверка тех же свойств в JasperGold;
- итоговые прогоны перед синтезом.

Сравнение с моделью по тактам уже закрывает большую часть того, что обычно проверяют SVA, поэтому SVA — последний шаг, а не срочный.

## Что известно про сервер

Проверено на `srv-eda-07` и `srv-eda-04`.

| Что | Значение |
|---|---|
| ОС | CentOS Linux 7 |
| glibc | 2.17 |
| Системный Python | 3.6.8 (не годится, cocotb 2 требует 3.9+) |
| `xrun` по умолчанию | 19.03-s009 (старый) |
| Интернет | есть (`curl https://pypi.org` отвечает 200) |
| Модули окружения | `module avail cadence` |

Доступные версии Xcelium: 19.03.009, 19.09.016, 20.09.011, 22.03, 23.09.001, **24.03.001**.
JasperGold: 2020.06, **2024.03**. Есть также vManager 19.03 и 21.09.

## Что известно про библиотеки

| Пакет | Под glibc 2.17 | Откуда ставить |
|---|---|---|
| cocotb 2.1.0 | есть | pip |
| pyuvm 5.0.0 | есть | pip |
| pytest | есть | pip |
| pyvsc | есть | pip |
| pyslang 11 | через pip **нет** (нужен glibc 2.27+), в conda-forge **есть** (glibc 2.17+) | conda-forge |

Вывод: всё ставится на сервере, pyslang берём из conda, а не из pip.

## План установки

1. Поставить Miniforge в домашнюю папку (права администратора не нужны, условия Anaconda принимать не нужно):

   ```bash
   wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   bash Miniforge3-Linux-x86_64.sh -b -p ~/miniforge3
   ~/miniforge3/bin/conda init bash
   source ~/.bashrc
   ```

2. Создать окружение:

   ```bash
   conda create -n reflection -c conda-forge python=3.11 pyslang=11 -y
   conda activate reflection
   python -m pip install cocotb==2.1.0 pyuvm==5.0.0 pytest
   ```

3. Подгрузить свежий Xcelium:

   ```bash
   module load cadence/XCELIUMMAIN/24.03.001
   xrun -version          # must say 24.03
   ```

   Если версия осталась 19.03: `module unload cadence/XCELIUMMAIN/19.03.009`, потом снова `module load`.

4. Забрать проект (`git clone` с GitHub, ветка `v2`) и запустить тесты модели, которым симулятор не нужен:

   ```bash
   python -m pytest tests -q --ignore=tests/test_uvm.py
   ```

   Тесты, которые сверяют модель с Icarus, на сервере пропустятся сами (там нет `iverilog`).

## Что нужно доделать в коде

- **Выбор симулятора.** В `Engine/Run.py` сейчас жёстко записан `icarus`. Нужна настройка `icarus` / `xcelium` (в `Project.py` или аргументом командной строки). Правка маленькая.
- **SVA.** Свойства отдельными файлами, например `hardware/sva/mac_q16_sva.sv`, подключение через `bind`. RTL остаётся чистым для Genus, те же файлы идут и в Xcelium, и в JasperGold. Разбор RTL (`Engine/Netlist.py`) нужно научить пропускать эти файлы; Icarus их не получает.

## Что не проверено

- Заведётся ли cocotb 2.1 с Xcelium 24.03 на CentOS 7. cocotb официально тестируется на RHEL 8 и новее, CentOS 7 в списке нет. Сборка cocotb под glibc 2.17 существует, так что шансы хорошие, но покажет только запуск.
- Встанет ли Miniforge на glibc 2.17. Должен: 2.17 — базовая система для conda-forge. Если свежий установщик откажется, взять версию постарше.
- Одинаково ли окружение на разных серверах (`srv-eda-04`, `srv-eda-07`).

## Что решили не делать

- **Verilator** — не нужен, раз есть Xcelium. Два симулятора локально поддерживать не будем.
- **Старый ModelSim из Quartus** — скорее всего, не поддерживает `assert property`, и с cocotb на Windows у него проблемы с разрядностью.
- **Перенос пакетов архивом** (`pip download`, `conda-pack`) — не нужен, на сервере есть интернет.
- **Сохранение списка цепей в JSON** как обход pyslang — не нужно, pyslang ставится из conda-forge.

## Порядок работ

1. Покрытие (локально, Icarus).
2. Короткий пробный заход на сервер: установка по плану выше и запуск текущего теста через `xrun`, без SVA. Цель — убедиться, что окружение работает, пока это не срочно.
3. SVA и JasperGold.
4. Golden-компоненты для остальных модулей ускорителя.

## Ссылки

- cocotb, поддерживаемые платформы: https://docs.cocotb.org/en/stable/platform_support.html
- cocotb, поддержка симуляторов: https://docs.cocotb.org/en/stable/simulator_support.html
- pyslang в conda-forge: https://anaconda.org/conda-forge/pyslang
- Miniforge: https://github.com/conda-forge/miniforge

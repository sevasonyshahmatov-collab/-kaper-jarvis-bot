"""Пробный прогон зеркала в Instagram (владелец 22.10): два последних поста канала с картинкой — владельцу превью картинки
и подписи; в Instagram ничего не выкладывается."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'mirror')))
import ig_mirror  # noqa: E402
ig_mirror.main(dry=True)

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from flask import Flask
import threading

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "8332350911:AAGibZDAVfo2IWue-vUAx0WhxKWCXTJmUjw"

# Создаем бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Создаём веб-сервер для Render
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running!"

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

# Определяем состояния
class States(StatesGroup):
    from_decimal_number = State()
    from_decimal_base = State()
    to_decimal_number = State()
    to_decimal_base = State()
    arithmetic_first = State()
    arithmetic_first_base = State()
    arithmetic_operation = State()
    arithmetic_second = State()
    arithmetic_second_base = State()
    arithmetic_result_base = State()

# ============ НОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С HEX ============

def validate_number_for_base(number_str, base):
    """Проверяет, что строка числа корректна для заданной системы счисления"""
    if not number_str:
        return False
    
    # Символы для систем счисления до 36
    valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    valid_chars = valid_chars[:base]
    
    # Проверяем каждый символ
    for char in number_str.upper():
        if char not in valid_chars:
            return False
    return True

def convert_to_decimal(number_str, base):
    """Перевод числа из любой системы в десятичную (поддерживает буквы A-F)"""
    if not number_str:
        raise ValueError("Пустое число")
    
    number_str = number_str.upper().strip()
    result = 0
    power = 0
    
    # Проходим по символам справа налево
    for char in reversed(number_str):
        if char.isdigit():
            digit = int(char)
        else:
            # Буквы A=10, B=11, и т.д.
            digit = ord(char) - ord('A') + 10
        
        if digit >= base:
            raise ValueError(f"Цифра {char} недопустима для системы {base}")
        
        result += digit * (base ** power)
        power += 1
    
    return result

def convert_from_decimal(number, base):
    """Перевод из десятичной системы в любую (результат может содержать буквы A-F)"""
    if number == 0:
        return "0"
    
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    n = abs(number)
    
    while n > 0:
        result = digits[n % base] + result
        n //= base
    
    return ("-" if number < 0 else "") + result

def calculate_arithmetic(num1_str, base1, num2_str, base2, operation, result_base):
    """Арифметические операции с поддержкой HEX"""
    # Преобразуем в десятичную
    dec1 = convert_to_decimal(num1_str, base1)
    dec2 = convert_to_decimal(num2_str, base2)
    
    # Выполняем операцию
    if operation == '+':
        result_dec = dec1 + dec2
    elif operation == '-':
        result_dec = dec1 - dec2
    elif operation == '*':
        result_dec = dec1 * dec2
    else:  # деление
        if dec2 == 0:
            raise ValueError("Деление на ноль!")
        result_dec = dec1 // dec2
    
    # Преобразуем результат в нужную систему
    return convert_from_decimal(result_dec, result_base)

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Из десятичной")],
        [KeyboardButton(text="📥 В десятичную")],
        [KeyboardButton(text="🧮 Арифметика")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

operation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕"), KeyboardButton(text="➖")],
        [KeyboardButton(text="✖️"), KeyboardButton(text="➗")],
        [KeyboardButton(text="🔙 Назад")]
    ],
    resize_keyboard=True
)

def safe_int(s):
    """Безопасное преобразование в целое число"""
    try:
        if isinstance(s, str):
            s = s.strip()
        return int(s)
    except (ValueError, TypeError):
        return None

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Я бот для перевода чисел и арифметических операций.\n"
        "✅ Поддерживаю системы счисления от 2 до 36\n"
        "✅ Буквы A-F для шестнадцатеричной системы\n"
        "✅ Проверяю корректность ввода\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📌 **Доступные команды:**\n"
        "/start - главное меню\n\n"
        "📝 **Примеры:**\n"
        "• Из десятичной: 42 → 2 → 101010\n"
        "• Из десятичной: 255 → 16 → FF\n"
        "• В десятичную: FF → 16 → 255\n"
        "• В десятичную: 1010 → 2 → 10\n"
        "• Арифметика: FF (16) + 10 (16) → 10 → 265\n\n"
        "⚠️ **Важно:**\n"
        "• Для систем >10 используйте буквы A-F\n"
        "• Буквы можно вводить в любом регистре\n"
        "• Недопустимые символы будут отклонены",
        reply_markup=main_keyboard
    )

@dp.message()
async def handle_message(message: Message, state: FSMContext):
    text = message.text.strip()
    current_state = await state.get_state()
    
    # Обработка кнопок меню
    if text == "📤 Из десятичной":
        await state.set_state(States.from_decimal_number)
        await message.answer(
            "Введите десятичное число (целое):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    elif text == "📥 В десятичную":
        await state.set_state(States.to_decimal_number)
        await message.answer(
            "Введите число (цифры и буквы A-F):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    elif text == "🧮 Арифметика":
        await state.set_state(States.arithmetic_first)
        await message.answer(
            "Введите первое число (цифры и буквы A-F):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    elif text == "❓ Помощь":
        await cmd_help(message)
        return
    elif text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_keyboard)
        return
    
    try:
        if current_state == States.from_decimal_number.state:
            num = safe_int(text)
            if num is None:
                await message.answer("❌ Ошибка! Введите целое число (например: 42, 255, 1000).")
                return
            await state.update_data(number=num)
            await state.set_state(States.from_decimal_base)
            await message.answer("Введите систему счисления (2-36):")
            
        elif current_state == States.from_decimal_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Ошибка! Введите число от 2 до 36.")
                return
            
            data = await state.get_data()
            number = data.get('number')
            
            try:
                result = convert_from_decimal(number, base)
                await message.answer(
                    f"✅ Результат:\n{number} (дес.) → {result} (сист.{base})",
                    reply_markup=main_keyboard
                )
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=main_keyboard)
            
            await state.clear()
            
        elif current_state == States.to_decimal_number.state:
            # Сохраняем число как строку (может содержать буквы)
            number_str = text.upper().strip()
            
            # Проверяем, что строка не пустая
            if not number_str:
                await message.answer("❌ Ошибка! Введите число.")
                return
            
            # Сохраняем строку, а не число
            await state.update_data(number_str=number_str)
            await state.set_state(States.to_decimal_base)
            await message.answer("Введите систему счисления исходного числа (2-36):")
            
        elif current_state == States.to_decimal_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Ошибка! Введите число от 2 до 36.")
                return
            
            data = await state.get_data()
            number_str = data.get('number_str')
            
            # Проверяем корректность ввода для данной системы
            if not validate_number_for_base(number_str, base):
                await message.answer(
                    f"❌ Ошибка! Число '{number_str}' содержит недопустимые символы для системы {base}.\n"
                    f"В {base}-ичной системе допустимы символы: 0-{base-1 if base <= 10 else '9 и A-' + chr(ord('A') + base - 11)}",
                    reply_markup=main_keyboard
                )
                await state.clear()
                return
            
            try:
                result = convert_to_decimal(number_str, base)
                await message.answer(
                    f"✅ Результат:\n{number_str} (сист.{base}) → {result} (дес.)",
                    reply_markup=main_keyboard
                )
            except ValueError as e:
                await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=main_keyboard)
            except Exception as e:
                await message.answer(f"❌ Ошибка при переводе: {str(e)}", reply_markup=main_keyboard)
            
            await state.clear()
            
        elif current_state == States.arithmetic_first.state:
            # Сохраняем первое число как строку
            num1_str = text.upper().strip()
            if not num1_str:
                await message.answer("❌ Ошибка! Введите число.")
                return
            await state.update_data(num1_str=num1_str)
            await state.set_state(States.arithmetic_first_base)
            await message.answer("Введите систему счисления первого числа (2-36):")
            
        elif current_state == States.arithmetic_first_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Ошибка! Введите число от 2 до 36.")
                return
            
            data = await state.get_data()
            num1_str = data.get('num1_str')
            
            # Проверяем корректность
            if not validate_number_for_base(num1_str, base):
                await message.answer(
                    f"❌ Ошибка! Число '{num1_str}' содержит недопустимые символы для системы {base}.",
                    reply_markup=main_keyboard
                )
                await state.clear()
                return
            
            await state.update_data(base1=base)
            await state.set_state(States.arithmetic_operation)
            await message.answer("Выберите операцию:", reply_markup=operation_keyboard)
            
        elif current_state == States.arithmetic_operation.state:
            op_map = {"➕": "+", "➖": "-", "✖️": "*", "➗": "/"}
            if text in op_map:
                await state.update_data(operation=op_map[text])
                await state.set_state(States.arithmetic_second)
                await message.answer(
                    "Введите второе число (цифры и буквы A-F):",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                await message.answer("Выберите операцию из меню!", reply_markup=operation_keyboard)
            
        elif current_state == States.arithmetic_second.state:
            num2_str = text.upper().strip()
            if not num2_str:
                await message.answer("❌ Ошибка! Введите число.")
                return
            await state.update_data(num2_str=num2_str)
            await state.set_state(States.arithmetic_second_base)
            await message.answer("Введите систему счисления второго числа (2-36):")
            
        elif current_state == States.arithmetic_second_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Ошибка! Введите число от 2 до 36.")
                return
            
            data = await state.get_data()
            num2_str = data.get('num2_str')
            
            if not validate_number_for_base(num2_str, base):
                await message.answer(
                    f"❌ Ошибка! Число '{num2_str}' содержит недопустимые символы для системы {base}.",
                    reply_markup=main_keyboard
                )
                await state.clear()
                return
            
            await state.update_data(base2=base)
            await state.set_state(States.arithmetic_result_base)
            await message.answer("Введите систему счисления для результата (2-36):")
            
        elif current_state == States.arithmetic_result_base.state:
            res_base = safe_int(text)
            if res_base is None or res_base < 2 or res_base > 36:
                await message.answer("❌ Ошибка! Введите число от 2 до 36.")
                return
            
            data = await state.get_data()
            num1_str = data.get('num1_str')
            base1 = data.get('base1')
            num2_str = data.get('num2_str')
            base2 = data.get('base2')
            operation = data.get('operation')
            
            try:
                result = calculate_arithmetic(num1_str, base1, num2_str, base2, operation, res_base)
                
                op_symbol = operation
                if op_symbol == '/':
                    op_symbol = '÷'
                
                await message.answer(
                    f"✅ Результат:\n{num1_str} {op_symbol} {num2_str} = {result} (сист.{res_base})",
                    reply_markup=main_keyboard
                )
            except ValueError as e:
                await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=main_keyboard)
            except Exception as e:
                await message.answer(f"❌ Ошибка при вычислении: {str(e)}", reply_markup=main_keyboard)
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике: {e}")
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}\nПожалуйста, начните заново с /start",
            reply_markup=main_keyboard
        )
        await state.clear()

# ГЛАВНАЯ ФУНКЦИЯ
async def main():
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    print("🚀 Бот запущен!")
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    print("🎯 Готов к работе!")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

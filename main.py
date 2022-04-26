import io
import logging
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State

from addNetwork import create_command


API_TOKEN = os.environ.get('API_TOKEN')
PROXY_URL = os.environ.get('http_proxy')

if not API_TOKEN:
    exit("Для работы бота необходимо задать API_TOKEN")


# Configure logging
logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()

# Initialize bot and dispatcher
# bot = Bot(token=API_TOKEN, proxy=PROXY_URL)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


class GenerateCLICommand(StatesGroup):
    file_zone = State()
    network_class_prefix = State()
    sub_index = State()
    blacklist = State()
    apply = State()


@dp.message_handler(commands='GenerateCLICommand')
async def cmd_start(message: types.Message):
    await GenerateCLICommand.file_zone.set()

    answer = [
        "Добавьте файл с префиксами",
        "",
        "Для отмены в любой момент отправите *Отмена*"
    ]

    await message.answer('\n'.join(answer), parse_mode="MarkdownV2", reply_markup=types.ReplyKeyboardRemove())


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='отмена')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info(f'User:{message.from_user.full_name}, user_id={message.from_user.id} Cancelling state {current_state}')
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отмена выполнена', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(content_types=['document'], state=GenerateCLICommand.file_zone)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        document = message.document
        file_info = await bot.get_file(document.file_id)

        # print(document)
        # print(file_info)

        # name = document.file_name
        # fi = file_info.file_path
        # urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{API_TOKEN}/{fi}', f'./{name}')
        # file = await bot.download_file_by_id(document.file_id, f'./{name}')
        file = await bot.download_file_by_id(document.file_id)
        # print(file.read())

        await bot.send_message(message.from_user.id, 'Файл успешно сохранён')

        data['document'] = document
        data['file_prefix'] = file_info
        data['file'] = file

    await GenerateCLICommand.next()

    await message.answer("Ввидите префикс для Network Class")


@dp.message_handler(state=GenerateCLICommand.network_class_prefix)
async def process_age(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['network_class_prefix'] = message.text

    await GenerateCLICommand.next()

    await message.answer(f"С Какого номера начать создавать Network Class?\nНапример 1\n{message.text}-1"
                         )


@dp.message_handler(lambda message: message.text.isdigit(), state=GenerateCLICommand.sub_index)
async def process_age(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['sub_index'] = int(message.text)

    await GenerateCLICommand.next()

    # Configure ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Требуется", "Нет")

    await message.answer("Требуется ли создавать BlackList?", reply_markup=markup)


@dp.message_handler(lambda message: message.text in ["Требуется", "Нет"], state=GenerateCLICommand.blacklist)
async def process_gender_invalid(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text.lower() == "нет":
            data['blacklist'] = False
        else:
            data['blacklist'] = True

        file_name = data['document']['file_name']

        networks_list = data['file'].read().split()
        data['file'].seek(0)
        network_class_prefix = data['network_class_prefix']
        blacklist = data['blacklist']
        sub_index = data['sub_index']

    answer = [
        f'Файс с префиксами: {file_name}',
        f'Количество строк: {len(networks_list)}',
        f'Первый Network Class: {network_class_prefix}-{sub_index}',
        f'Cоздание blacklist: {blacklist}'
    ]

    await message.answer('\n'.join(answer))

    await GenerateCLICommand.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Да", "Отмена")

    answer = "Все правельно?"

    return await message.answer(answer, reply_markup=markup)


@dp.message_handler(lambda message: message.text not in ["Да"], state=GenerateCLICommand.apply)
async def process_gender_invalid(message: types.Message):
    return await message.delete()


@dp.message_handler(state=GenerateCLICommand.apply)
async def process_gender_invalid(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        networks_list = data['file'].read().decode().split()
        network_class_prefix = data['network_class_prefix']
        blacklist = data['blacklist']
        start_number_class = data['sub_index']

        file_name = f'cli_command_{network_class_prefix}'

    await state.finish()

    command_list, error_list = create_command(networks_list, network_class_prefix, start_number_class, blacklist)

    if command_list:
        file_obj = io.BytesIO("\n".join(command_list).encode())
        file_obj.name = f"{file_name}.txt"

        return await bot.send_document(message.from_user.id, file_obj, caption="Файл с командами",
                                       reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Произошла ошибка!")


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    answer = [
        f"Привет, {message['from']['first_name']}!",
        "Я могу по файлу с сетями,",
        "создать список команд для DefensePro v8,",
        "чтобы добавить эти сети в Network Class",
        "",
        "Просто отправь команду /GenerateCLICommand"
    ]

    await message.answer('\n'.join(answer))


@dp.message_handler(regexp="^привет")
async def echo(message: types.Message):
    # old style:
    # await bot.send_message(message.chat.id, message.text)

    await message.reply(message.text)


@dp.message_handler(state='*')
async def message_delete(message: types.Message):
    await message.delete()


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


async def startup(_):
    print("Bot online")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=startup, on_shutdown=shutdown)

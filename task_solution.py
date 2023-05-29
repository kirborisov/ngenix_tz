import concurrent.futures
import os
import zipfile
import csv
import uuid
import random
from typing import Tuple, List
from lxml import etree
from lxml.etree import _Element
from concurrent.futures import ProcessPoolExecutor


class AppConfig:
    def __init__(self, num_zip_files, num_xml_in_zip, path_zips):
        self.num_zip_files = num_zip_files
        self.num_xml_in_zip = num_xml_in_zip
        self.path_zips = self.mkdir_if_not_exists(path_zips)

    def mkdir_if_not_exists(self, path_zips):
        if not os.path.exists(path_zips):
            try:
                os.makedirs(path_zips)
            except OSError as e:
                print("Error: %s : %s" % (path_zips, e.strerror))

        return path_zips


class XMLCreator:
    """ Создание xml файлов со случайными данными следующей структуры:
        <root>
            <var name=’id’ value=’<случайное уникальное строковое значение>’/>
            <var name=’level’ value=’<случайное число от 1 до 100>’/>
            <objects>
                <object name=’<случайное строковое значение>’/>
                <object name=’<случайное строковое значение>’/>
                …
            </objects>
        </root>
        В тэге objects случайное число (от 1 до 10) вложенных тэгов object.
    """

    def create(self) -> str:
        root = self.create_root()
        return etree.tostring(root, pretty_print=True).decode()

    def create_random_object(self) -> _Element:
        return etree.Element("object", name=str(uuid.uuid4()))

    def create_random_objects(self) -> _Element:
        objects_element = etree.Element("objects")
        for __ in range(random.randint(1, 10)):
            objects_element.append(self.create_random_object())
        return objects_element

    def create_root(self) -> _Element:
        root = etree.Element("root")
        root.append(etree.Element("var", name="id",
                                  value=self.gen_random_str()))
        root.append(etree.Element("var", name="level",
                                  value=str(random.randint(1, 100))))
        root.append(self.create_random_objects())
        return root

    def gen_random_str(self):
        return str(uuid.uuid4())


class ZIPCreator:
    """ Создание zip-архивов, в каждом N xml файлов со случайными данными. """

    def __init__(self, config: AppConfig):
        self.config = config

    def create(self) -> None:
        xml_creator = XMLCreator()
        zip_file_name = os.path.join(
            config.path_zips, f'{self.gen_filename()}.zip'
        )
        # Создание zip архива
        with zipfile.ZipFile(zip_file_name, 'w') as zip_file:
            for _ in range(self.config.num_xml_in_zip):
                xml_file_name = f'{self.gen_filename()}.xml'
                zip_file.writestr(xml_file_name, xml_creator.create())

    def gen_filename(self) -> str:
        return str(uuid.uuid4())


class XMLParser:
    """  Обработка директории с полученными zip архивами, разборка вложенных
        xml файлов и формирование 2х csv файлов:
        Первый: id, level - по одной строке на каждый xml файл
        Второй: id, object_name - по отдельной строке для каждого
            тэга object (получится от 1 до 10 строк на каждый xml файл) """
    def __init__(self, config: AppConfig):
        self.config = config

    def parse_xml(self, xml_content: bytes) -> Tuple[_Element, _Element, List]:
        root = etree.fromstring(xml_content)

        id_value = root.xpath("./var[@name='id']/@value")[0]
        level_value = root.xpath("./var[@name='level']/@value")[0]

        object_names = root.xpath('./objects/object/@name')

        return id_value, level_value, object_names

    def parse_zip(self, zip_file_path: str) -> Tuple[List, List]:
        csv_data_1 = []
        csv_data_2 = []

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            name_list = zip_ref.namelist()
            xml_files = [file for file in name_list if file.endswith('.xml')]

            for xml_file in xml_files:
                with zip_ref.open(xml_file) as f:
                    xml_content = f.read()

                    id_value, level_value, object_names = self.parse_xml(xml_content)

                    csv_data_1.append((id_value, level_value))

                    object_tuples = [(id_value, obj_name) for obj_name in object_names]
                    csv_data_2.extend(object_tuples)

        return csv_data_1, csv_data_2

    def get_zip_files(self, directory: str) -> list:
        return [file for file in os.listdir(directory) if file.endswith('.zip')]

    def write_csv(self, csv_data_1: list, csv_data_2: list) -> None:
        self.write_file('output_1.csv', csv_data_1)
        self.write_file('output_2.csv', csv_data_2)

    def write_file(self, filename, csv_data):
        filepath = os.path.join(self.config.path_zips, filename)
        with open(filepath, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)


def process_delete_old_zip(config):
    """ Удаление архивов из предыдущего запуска. """
    files = os.listdir(config.path_zips)

    for file in files:
        if file.endswith('.zip'):
            os.remove(os.path.join(config.path_zips, file))


def process_create_zip(config: AppConfig):
    """ Создание архивов с xml. """
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _ in range(config.num_zip_files):
            executor.submit(ZIPCreator(config).create)


def process_create_csv(config: AppConfig):
    """ Создание CSV файлов из XML данных. """
    csv_data_1 = []
    csv_data_2 = []

    xml_parser = XMLParser(config)
    zip_files = xml_parser.get_zip_files(config.path_zips)

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(
                        xml_parser.parse_zip,
                        os.path.join(
                            config.path_zips, zip_file
                        )
                    ) for zip_file in zip_files]

        for future in futures:
            result = future.result()

            csv_data_1.extend(result[0])
            csv_data_2.extend(result[1])

    xml_parser.write_csv(csv_data_1, csv_data_2)


if __name__ == '__main__':
    config = AppConfig(
                num_zip_files=50,
                num_xml_in_zip=100,
                path_zips=f'{os.path.dirname(os.path.abspath(__file__))}/zips'
            )
    # если нужно удалить данные предыдущего запуска
    process_delete_old_zip(config)
    # 1-я часть ТЗ
    process_create_zip(config)
    # 2-я часть ТЗ
    process_create_csv(config)

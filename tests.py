import unittest
from lxml import etree
from task_solution import AppConfig, XMLCreator, XMLParser
import csv
import os
from zipfile import ZipFile



class TestXMLCreator(unittest.TestCase):
    def setUp(self):
        self.creator = XMLCreator()

    def test_create_random_object(self):
        element = self.creator.create_random_object()
        self.assertEqual(element.tag, "object")
        self.assertTrue("name" in element.attrib)
        
    def test_create_random_objects(self):
        element = self.creator.create_random_objects()
        self.assertEqual(element.tag, "objects")
        self.assertTrue(1 <= len(element) <= 10)
        for child in element:
            self.assertEqual(child.tag, "object")
            self.assertTrue("name" in child.attrib)
            
    def test_create_root(self):
        root = self.creator.create_root()
        self.assertEqual(root.tag, "root")
        self.assertEqual(len(root), 3)
        self.assertEqual(root[0].tag, "var")
        self.assertEqual(root[0].attrib["name"], "id")
        self.assertEqual(root[1].tag, "var")
        self.assertEqual(root[1].attrib["name"], "level")
        self.assertTrue(1 <= int(root[1].attrib["value"]) <= 100)
        self.assertEqual(root[2].tag, "objects")
        
    def test_create(self):
        xml = self.creator.create()
        root = etree.fromstring(bytes(xml, encoding='utf-8'))
        self.assertEqual(root.tag, "root")
        self.assertEqual(len(root), 3)
        self.assertEqual(root[0].tag, "var")
        self.assertEqual(root[0].attrib["name"], "id")
        self.assertEqual(root[1].tag, "var")
        self.assertEqual(root[1].attrib["name"], "level")
        self.assertTrue(1 <= int(root[1].attrib["value"]) <= 100)
        self.assertEqual(root[2].tag, "objects")


class TestXMLParser(unittest.TestCase):
    def setUp(self):
        config = AppConfig(
                    num_zip_files=50,
                    num_xml_in_zip=100,
                    path_zips=f'{os.path.dirname(os.path.abspath(__file__))}/zips'
                )
        self.parser = XMLParser(config)

    def test_parse_xml(self):
        xml_content = b"""<root>
                            <var name='id' value='1234'/>
                            <var name='level' value='15'/>
                            <objects>
                                <object name='obj1'/>
                                <object name='obj2'/>
                            </objects>
                        </root>"""
        id_value, level_value, object_names = self.parser.parse_xml(xml_content)
        self.assertEqual(id_value, '1234')
        self.assertEqual(level_value, '15')
        self.assertEqual(object_names, ['obj1', 'obj2'])

    def test_parse_zip(self):
        zip_file_name = 'test.zip'
        with ZipFile(zip_file_name, 'w') as zip_file:
            for i in range(3):
                xml_content = f"""<root>
                                    <var name='id' value='id{i}'/>
                                    <var name='level' value='15'/>
                                    <objects>
                                        <object name='obj1'/>
                                        <object name='obj2'/>
                                    </objects>
                                </root>"""
                zip_file.writestr(f'test{i}.xml', xml_content)
        
        csv_data_1, csv_data_2 = self.parser.parse_zip(zip_file_name)
        self.assertEqual(
                csv_data_1, 
                [
                    ('id0', '15'),
                    ('id1', '15'),
                    ('id2', '15')
                ])
        self.assertEqual(
                csv_data_2,
                [
                    ('id0', 'obj1'),
                    ('id0', 'obj2'),
                    ('id1', 'obj1'),
                    ('id1', 'obj2'),
                    ('id2', 'obj1'),
                    ('id2', 'obj2')
                ])
        os.remove(zip_file_name)

    def test_write_csv(self):
        csv_data_1 = [
                ('id0', '15'),
                ('id1', '15'),
                ('id2', '15')
                ]
        csv_data_2 = [
                ('id0', 'obj1'),
                ('id0', 'obj2'),
                ('id1', 'obj1'),
                ('id1', 'obj2'),
                ('id2', 'obj1'),
                ('id2', 'obj2')
                ]
        self.parser.write_csv(csv_data_1, csv_data_2)

        path_csv_1 = os.path.join(
                self.parser.config.path_zips, 'output_1.csv'
        )
        path_csv_2 = os.path.join(
                self.parser.config.path_zips, 'output_2.csv'
        )

        # Проверка содержимого файлов
        with open(path_csv_1, 'r') as file:
            reader = csv.reader(file)
            reader = [tuple(l) for l in reader]
            self.assertEqual(list(reader), csv_data_1)

        with open(path_csv_2, 'r') as file:
            reader = csv.reader(file)
            reader = [tuple(l) for l in reader]
            self.assertEqual(list(reader), csv_data_2)

        os.remove(path_csv_1)
        os.remove(path_csv_2)



if __name__ == '__main__':
    unittest.main() 

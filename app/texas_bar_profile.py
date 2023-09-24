"""
texas_bar_profile.py - Retrieve Texas Bar Profile from www.texasbar.com
"""

import time
import sqlite3

import requests
from bs4 import BeautifulSoup


PAUSE_MAX = 25  # Pause for a few seconds after every group to let the web site breath...good citizenship
PAUSE_SECONDS = 3  # Duration of pause between batches
PAGE_MAX = 200  # Number to retrieve per page
DENTON_COUNTY = '61'
COLLIN_COUNTY = '43'
DALLAS_COUNTY = '57'


class TexasBarProfile():
    """
    Retrieve attorney profile from www.texasbar.com
    """
    def __init__(self):
        """
        Class initializer.

        Args:
            None
        """
        self.search_url = 'https://www.texasbar.com/AM/Template.cfm?Section=Find_A_Lawyer&Template=/CustomSource/MemberDirectory/Result_form_client.cfm'
        self.base_url = 'https://www.texasbar.com'

        # Do not mess with these without testing it, e.g. at web.postman.co. The server is sensitive.
        self.data = {
            # 'PracticeArea': '',
            'PPlCityName': '',
            'County': '',
            'State': '',
            'Zip': '75093',
            'Name': '',
            'CompanyName': '',
            'BarCardNumber': '',
            'Submitted': '1',
            'ShowPrinter': '1',
            # 'MaxNumber': PAGE_MAX,
            'Find': '0'
        }

    def retrieve(self, city:str = '', county:str = '', state:str = '', zip_code:str = '', name:str = '', company:str = '', barcard:str = '', page:int = 0):
        """
        Retrieve the HTML page for the given attorney from the web site.

        Args:
            city (str): City Name to search for
            county (str): County Name to search for
            state (str): State abbreviation to search for
            zip (str): ZIP Code to search for
            name (str): Attorney name to search for
            company (str): Company or Firm Name to search for
            barcard (str): Bar card number to search for

        Results:
            (str): String content retrieved from site
        """
        # Do not mess with these without testing it, e.g. at web.postman.co. The server is sensitive.
        self.data['PracticeArea'] = '42,25,47,52,40,54'
        self.data['PPlCityName'] = city
        self.data['County'] = county
        self.data['State'] = state
        self.data['Zip'] = zip_code
        self.data['Name'] = name
        self.data['CompanyName'] = company
        self.data['BarCardNumber'] = barcard
        self.data['ShowPrinter'] = '1'
        self.data['Submitted'] = '1'
        self.data['Find'] = '0'
        # self.data['TBLSCertified'] = ''  # Not working on their site as of 01/09/2022 TJD

        if page > 0:
            self.data['SortName'] = ''
            self.data['FirstName'] = ''
            self.data['Name'] = ''
            self.data['LastName'] = ''
            self.data['InformalName'] = ''
            self.data['Region'] = ''
            self.data['Country'] = ''
            self.data['FilterName'] = ''
            self.data['ShowOnlyTypes'] = ''
            self.data['BarDistrict'] = ''
            self.data['TYLADistrict'] = ''
            self.data['Start'] = ''
            self.data['MaxNumber'] = PAGE_MAX
            self.data['Page'] = page * PAGE_MAX + 1
            self.data['Prev'] = (page - 1) * PAGE_MAX + 1
            self.data['Next'] = page * PAGE_MAX + 1
            self.data['ButtonName'] = 'Page'

        success = False
        while not success:
            try:
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                result = requests.post(self.search_url, data=self.data, headers=headers)
                success = True
            except Exception:  # pylint: disable=broad-except
                print(f"ConnectionError trying to retrieve page {page}...retrying")
                time.sleep(5)
        return result

    def parse(self, result) -> list:
        """
        Parse content retrieved from web site.

        Args:
            result: Result from self.retrieve()

        Returns:
            (list): List of dict of Attorney profile
        """
        soup = BeautifulSoup(result.content, "html.parser")
        lawyers = soup.find_all("article", class_="lawyer")
        result = list(self.extract(lawyers))
        return result

    def extract(self, lawyers) -> list:
        """
        Extract a lawer from each item in the lawers list
        """
        pause_counter = 0
        lawyer_count = len(lawyers)
        bar_length = 100
        bars = "#" * bar_length
        for idx, lawyer in enumerate(lawyers):
            bar_segs = int(((idx + 1) / lawyer_count) * 100)
            print('\r'+bars[0:bar_segs].ljust(bar_length, '.'), end='')
            pause_counter += 1
            if pause_counter > PAUSE_MAX:
                pause_counter = 0
                print("\rPausing", end='')
                time.sleep(PAUSE_SECONDS)
                print("\rResumed", end='')
            fname = ''
            mname = ''
            address = ''

            prefix = lawyer.find('span', class_='honorific-prefix')

            # Sometimes the first name and last name are in separate 'given-name' elements.
            # Othertimes the first and middle name are in the same element separated by space.
            gnames = lawyer.find_all('span', class_='given-name')
            if gnames:
                fname = gnames[0].text.strip()
            if len(gnames) > 1:
                mname = gnames[1].text.strip()
            elif ' ' in fname:
                fname, mname = fname.split(' ', 1)

            additional_name = lawyer.find('span', class_='additional-name')
            if additional_name:
                additional_name = additional_name.text.strip()[1:-1]
            else:
                additional_name = ''
            lname = lawyer.find('span', class_='family-name')
            suffix = lawyer.find('span', class_='honorific-suffix')
            firm = lawyer.find('h5')
            address_tag = lawyer.find('p', class_='address')
            if address_tag:
                address = parse_address(address_tag)
            try:
                telephone = lawyer.find('a', href=lambda x: "tel:" in x.lower()).text.strip()
            except AttributeError:
                telephone = ''

            # Get the detailed record to retrieve the bar number and admittance date.
            detail_url = lawyer.find('a', href=lambda x: 'a' in x.lower())['href']
            success = False
            while not success:
                try:
                    result = requests.get(self.base_url + detail_url)
                    success = True
                except Exception:  # pylint: disable=broad-except
                    print(f"ConnectionError trying to retreive data for Atty {fname} {mname} {lname}...retrying")
                    time.sleep(5)
            soup = BeautifulSoup(result.content, "html.parser")
            d_lawyer = soup.find("article", class_="lawyer")
            bar_no_label = d_lawyer.find("strong",text=lambda x: x and "bar card number" in x.lower())
            bar_no = bar_no_label.next_sibling
            license_date_label = d_lawyer.find("strong",text=lambda x: x and "tx license date" in x.lower())
            license_date = license_date_label.next_sibling
            practice_areas = soup.find('p', class_='areas')
            if practice_areas is not None:
                practice_areas = practice_areas.get_text()
                practice_areas = practice_areas \
                    .replace('Practice Areas:', '') \
                    .replace('\n', '') \
                    .replace('\r', '') \
                    .replace('<strong>', '') \
                    .replace('</strong>', '') \
                    .strip()

            attorney = {
                'bar_number': bar_no.text.strip(),
                'license_date': license_date.text.strip(),
                'prefix': prefix.text.strip(),
                'fname': fname,
                'mname': mname,
                'lname': lname.text.strip(),
                'suffix': suffix.text.strip(),
                'firm': firm.text.strip(),
                'address': address,
                'familiar_name': additional_name,
                'telephone': telephone.replace('Tel: ', ''),
                'detail_url': detail_url,
                'practice_areas': practice_areas
            }

            print(
                attorney['bar_number'],
                attorney['fname'].ljust(10),
                attorney['mname'].ljust(10),
                attorney['lname'].ljust(10),
                attorney['address']
            )

            yield attorney


def parse_address(address) -> dict:
    """
    Parse an address string into a dict of subparts.
    """
    state = ''
    zip_code = ''

    # Sometimes there are two <br> tags and sometimes there is only one.
    # If there are two, we'll get two children, one for the street, the other with CSZ.
    # If there is one, we'll get street in the first child and nothing in the second.
    parts = [child.text.strip() for child in address.children]

    if parts[1] == '':
        parts = [s.strip() for s in address.strings]

    street = parts[0]
    parts = parts[1].split(',')
    city = parts[0]
    if len(parts) > 1:
        parts = parts[1].split('\xa0')
        state = parts[0]
        if len(parts) > 1:
            zip_code = parts[1]
    result = {
        'street': street,
        'city': city,
        'state': state,
        'zip': zip_code
    }
    return result


def drop_table():
    """
    Drop the database table if it exists.
    """
    conn = sqlite3.connect('TexasBarProfile.db')
    cursor = conn.cursor()
    cursor.execute('''DROP TABLE IF EXISTS attorneys''')
    conn.commit()
    conn.close()


def create_table():
    """
    Create the database table if it does not already exist.
    """
    conn = sqlite3.connect('TexasBarProfile.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS attorneys
        (bar_number text, license_date text, prefix text, fname text, mname text, lname text, suffix text, firm text, street text, city text, state text, zip text, familiar_name text, telephone text, detail_url text, practice_areas text, page integer, county text)''')
    cursor.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_bar_number ON attorneys(bar_number)''')
    conn.commit()
    conn.close()

def insert_attorney(attorney: dict, page: int):
    """
    Insert an attorney into the database.
    """
    if not isinstance(attorney.get('address'), dict):
        attorney['address'] = {}
    conn = sqlite3.connect('TexasBarProfile.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO attorneys VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        attorney['bar_number'],
        attorney.get('license_date'),
        attorney.get('prefix'),
        attorney.get('fname'),
        attorney.get('mname'),
        attorney.get('lname'),
        attorney.get('suffix'),
        attorney.get('firm'),
        attorney.get('address', {}).get('street'),
        attorney.get('address', {}).get('city'),
        attorney.get('address', {}).get('state'),
        attorney.get('address', {}).get('zip'),
        attorney.get('familiar_name'),
        attorney.get('telephone'),
        attorney.get('detail_url'),
        attorney.get('practice_areas'),
        page,  # saving the page number helps us recover from a crash
        'Dallas'
    ))
    conn.commit()
    conn.close()

def main():
    """
    Main entry point for the script.
    """
    create_table()
    searcher = TexasBarProfile()
    page = 0
    count = 0
    params = {
        'county': DALLAS_COUNTY,
    }
    # result = searcher.retrieve(company="KoonsFuller")
    result = searcher.retrieve(**params)
    batch = searcher.parse(result)
    try:
        while batch:
            count += len(batch)
            print('Processed page:', page, 'Count:', len(batch), 'Total:', count)
            for attorney in batch:
                insert_attorney(attorney, page)
            page += 1
            result = searcher.retrieve(page=page, **params)
            batch = searcher.parse(result)
    except Exception as exception:  # pylint: disable=broad-except
        print("Wrapping up due to exception:", exception)

if __name__ == '__main__':
    main()

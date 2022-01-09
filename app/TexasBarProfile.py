# TexasBarProfile.py - Retrieve Texas Bar Profile from www.texasbar.com

import requests
import time

from bs4 import BeautifulSoup


PAUSE_MAX = 25  # Pause for a few seconds after every group to let the web site breath...good citizenship
PAUSE_SECONDS = 3  # Duration of pause between batches
PAGE_MAX = 200  # Number to retrieve per page

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
            'PPlCityName': '',
            'County': '',
            'State': '',
            'Zip': '75093',
            'Name': '',
            'CompanyName': '',
            'BarCardNumber': '',
            'Submitted': '1',
            'ShowPrinter': '1',
            'MaxNumber': PAGE_MAX,
            'Find': '0'
        }

    def retrieve(self, city:str = '', county:str = '', state:str = '', zip:str = '', name:str = '', company:str = '', barcard:str = '', page:int = 0):
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
        self.data['PPlCityName'] = city
        self.data['County'] = county
        self.data['State'] = state
        self.data['Zip'] = zip
        self.data['Name'] = name
        self.data['CompanyName'] = company
        self.data['BarCardNumber'] = barcard
        self.data['MaxNumber'] = PAGE_MAX
        self.data['ShowPrinter'] = '1'
        self.data['Submitted'] = '1'
        self.data['Find'] = '0'
        # self.data['TBLSCertified'] = ''  # Not working on their site as of 01/09/2022 TJD

        if page > 0:
            self.data['Page'] = '0'
            self.data['Prev'] = (page - 1) * PAGE_MAX + 1
            self.data['Next'] = page * PAGE_MAX + 1
            self.data['ButtonName'] = 'Next'

        result = requests.post(self.search_url, self.data)
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
        result = [lawyer for lawyer in self.extract(lawyers)]
        return result

    def extract(self, lawyers) -> list:
        """
        Extract a lawer from each item in the lawers list
        """
        pause_counter = 0
        lawyer_count = len(lawyers)
        bar_length = 100
        bar = "#" * bar_length
        for idx, lawyer in enumerate(lawyers):
            bar_segs = int(((idx + 1) / lawyer_count) * 100)
            print('\r'+bar[0:bar_segs].ljust(bar_length, '.'), end='')
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
            result = requests.get(self.base_url + detail_url)
            soup = BeautifulSoup(result.content, "html.parser")
            d_lawyer = soup.find("article", class_="lawyer")
            bar_no_label = d_lawyer.find("strong",text=lambda x: x and "bar card number" in x.lower())
            bar_no = bar_no_label.next_sibling
            license_date_label = d_lawyer.find("strong",text=lambda x: x and "tx license date" in x.lower())
            license_date = license_date_label.next_sibling

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
                'detail_url': detail_url
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
    zip = ''

    # Sometimes there are two <br> tags and sometimes there is only one.
    # If there are two, we'll get two children, one for the street, the other with CSZ.
    # If there is one, we'll get street in the first child and nothing in the second.
    parts = [child.text.strip() for child in address.children]
    z = [child for child in address.children]

    if parts[1] == '':
        parts = [s.strip() for s in address.strings]

    street = parts[0]
    parts = parts[1].split(',')
    city = parts[0]
    if len(parts) > 1:
        parts = parts[1].split('\xa0')
        state = parts[0]
        if len(parts) > 1:
            zip = parts[1]
    result = {
        'street': street,
        'city': city,
        'state': state,
        'zip': zip
    }
    return result

def main():
    searcher = TexasBarProfile()
    attorneys = []
    page = 0
    result = searcher.retrieve(company="KoonsFuller")
    batch = searcher.parse(result)
    while batch:
        attorneys += batch
        page += 1
        result = searcher.retrieve(page=page)
        batch = searcher.parse(result)
    print()
    for idx, attorney in enumerate(attorneys):
        if attorney:
            print(
                f"{idx+1}".rjust(5)+". ",
                attorney['lname'].ljust(15),
                attorney['fname'].ljust(15),
                attorney['firm'].ljust(50),
                attorney['address']['city'].ljust(15),
                attorney['telephone'].ljust(12)
            )
        pass

if __name__ == '__main__':
    main()

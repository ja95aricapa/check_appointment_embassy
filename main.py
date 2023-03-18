import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def get_authenticity_token(login_url, headers):
    """Get the authenticity token and session

    Args:
        login_url (str): Login URL
        headers (dict): Headers

    Returns:
        session (obj): Session
        authenticity_token (str): Authenticity token
    """
    session = requests.Session()
    response = session.get(login_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    authenticity_token = soup.find('input', {'name': 'authenticity_token'})['value']
    return session, authenticity_token

def login(session, login_url, authenticity_token, headers, email, password):
    """Login to the website

    Args:
        session (obj): Session
        login_url (str): Login URL
        authenticity_token (str): Authenticity token
        headers (dict): Headers
        email (str): Email
        password (str): Password

    Raises:
        Exception: Failed to login

    Returns:
        None
    """
    data = {
        'authenticity_token': authenticity_token,
        'user[email]': email,
        'user[password]': password,
        'commit': 'Log in'
    }
    response = session.post(login_url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception("Failed to login: {}".format(response.status_code))

def get_current_dates(session, headers):
    """Get the current appointment dates

    Args:
        session (obj): Session
        headers (dict): Headers

    Returns:
        consulate_date (str): Consulate date
        cas_date (str): CAS date
    """
    response = session.get('https://ais.usvisa-info.com/es-co/niv/schedule/47029779/calendar', headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    consulate_date = soup.find('div', {'class': 'consulate-date'}).text.strip()
    cas_date = soup.find('div', {'class': 'cas-date'}).text.strip()
    return consulate_date, cas_date

def search_available_date(reschedule_url, session, headers, current_date):
    """Search for an available date

    Args:
        reschedule_url (str): Reschedule URL
        session (obj): Session
        headers (dict): Headers
        current_date (str): Current date

    Returns:
        date (str): Available date or None
    """
    response = session.get(reschedule_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    available_dates = soup.find_all('a', {'class': 'calendar-date'})
    for date in available_dates:
        if date.text.strip() != current_date:
            return date['href']
    return None

def reschedule_appointment(session, reschedule_url, headers, new_date):
    """Reschedule appointment

    Args:
        session (obj): Session
        reschedule_url (str): Reschedule URL
        headers (dict): Headers
        new_date (str): New date

    Raises:
        Exception: Failed to reschedule appointment

    Returns:
        None
    """
    response = session.get(new_date, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    authenticity_token = soup.find('input', {'name': 'authenticity_token'})['value']
    data = {
        '_method': 'patch',
        'authenticity_token': authenticity_token,
        'commit': 'Next'
    }
    response = session.post(reschedule_url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception("Failed to reschedule appointment: {}".format(response.status_code))

def logout(session, logout_url, headers):
    """Logout from the website

    Args:
        session (obj): Session
        logout_url (str): Logout URL
        headers (dict): Headers

    Returns:
        None
    """
    session.get(logout_url, headers=headers)
    session.close()
    print('Session closed')


def find_and_reschedule_appointment():
    """Find and reschedule appointment

    Retruns:
        None
    """
    # Define las credenciales de inicio de sesión
    login_url = os.getenv('URL_LOGIN')
    reschedule_url = os.getenv('URL_RESCHEDULE')
    logout_url = os.getenv('URL_LOGOUT')
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    try:
        # Get authentication token and session
        session, authenticity_token = get_authenticity_token(login_url, headers)

        # Login
        login(session, login_url, authenticity_token, headers, email, password)

        # Get current appointment dates
        fecha_consulado, fecha_cas = get_current_dates(session, headers)

        # Search for an available date at the CAS
        fecha_disponible_cas = search_available_date(reschedule_url, session, headers, fecha_cas)

        if fecha_disponible_cas:
            print('An available date was found at the CAS: ', fecha_disponible_cas)
            # Reschedule appointment at the CAS
            reschedule_appointment(session, reschedule_url, headers, fecha_disponible_cas)
            print('The appointment has been successfully rescheduled at the CAS.')
            return

        # Search for an available date at the Consulate
        fecha_disponible_consulado = search_available_date(reschedule_url, session, headers, fecha_consulado)

        if fecha_disponible_consulado:
            print('An available date was found at the Consulate: ', fecha_disponible_consulado)
            # Reschedule appointment at the Consulate
            reschedule_appointment(session, reschedule_url, headers, fecha_disponible_consulado)
            print('The appointment has been successfully rescheduled at the Consulate.')
            return

        print('No available dates were found at the CAS or Consulate.')
    except Exception as e:
        print('Error:', e)
    finally:
        # Close session
        logout(session, logout_url, headers)

if __name__ == '__main__':
    find_and_reschedule_appointment()

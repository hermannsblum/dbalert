import requests
from dateutil.parser import parse
from datetime import datetime, timedelta
import smtplib
from email.utils import formataddr
from email.message import EmailMessage
import click
from os import path
#from joblib import Memory

#memory = Memory('/tmp')

TIMEFORMAT = '%d.%m.%y, %H:%M'


#@memory.cache
def get_data(station_id, lookahead=180):
  # first get the name of the station
  r = requests.get(f'https://bahn.expert/api/stopPlace/v1/{station_id}')
  station = r.json()['name']
  r = requests.get(
      f'https://bahn.expert/api/iris/v2/abfahrten/{station_id}?lookahead={lookahead}&lookbehind=0'
  )
  return {'station_name': station, **r.json()}


def log_train(t, comment=''):
  delay = t.get('arrival', t.get('departure', dict(delay='nan'))).get('delay', 'nan')
  if 'departure' in t:
    departure = parse(t['departure']['time']).replace(tzinfo=None)
    print(f"{t['train']['name']}, delay {delay}, departure {departure.strftime(TIMEFORMAT)}: {comment}")
  else:
    print(f"{t['train']['name']}, delay {delay}, no departure: {comment}")

def get_text(station_id, time_to_station, min_delay, lookahead):
  print('Getting station data...')
  d = get_data(station_id, lookahead=lookahead)
  print(
      f"Checking {len(d['departures'])} departures from {d['station_name']}...")
  out = ""
  for t in d['departures']:
    if t['train']['type'] not in ('IC', 'EC', 'ICE', 'ECE'):
      continue
    delay = t.get('arrival', t.get('departure', dict(delay=0))).get('delay', 0)
    if delay < min_delay:
      log_train(t, 'too small delay')
      continue
    if t.get('cancelled', False):
      log_train(t, 'cancelled')
      continue
    if 'departure' not in t:
      log_train(t, 'arrival only')
      continue
    scheduled = parse(t['departure']['scheduledTime']).replace(tzinfo=None)
    departure = parse(t['departure']['time']).replace(tzinfo=None)
    if departure < (datetime.now() + timedelta(minutes=time_to_station)):
      log_train(t, 'departure too soon')
      continue
    out += f"Zug: {t['train']['name']}\nZiel: {t['destination']}\nAbfahrt gem. Fahrplan {scheduled.strftime(TIMEFORMAT)}\nAbfahrt gem. Realität {departure.strftime(TIMEFORMAT)}\nAktuelle Verspätung:  {t['arrival']['delay']} min\nGleis {t['departure']['platform']}\n\n"
  return out, d['station_name']


def validate_smtp(ctx, param, value):
  """Either all or none smtp parameters should be set."""
  if (value is None) and any(
      k.startswith('smtp') and ctx.params[k] for k in ctx.params):
    raise click.BadOptionUsage(param,
                               "Either all or no SMTP options need to be set.")
  return str(value)


@click.command()
@click.option('--station-id',
              default='8000207',
              envvar='DBALERT_STATIONID',
              show_default=True,
              help='station to query for delayed trains')
@click.option(
    '--time-to-station',
    default=30,
    envvar='DBALERT_TIMETOSTATION',
    help=
    '[minutes] Time it takes from user to the station. Only trains with an estimated departure at least this time ahead will be considered.'
)
@click.option(
    '--min-delay',
    default=60,
    envvar='DBALERT_MINDELAY',
    help='[minutes] Only trains with at least this delay will be considered')
@click.option(
    '--lookahead',
    default=180,
    envvar='DBALERT_LOOKAHEAD',
    help=
    '[minutes] Considers all trains regularly departing in the next X minutes.')
@click.option('--smtp-from',
              type=str,
              envvar='DBALERT_SMTP_FROM',
              callback=validate_smtp)
@click.option('--smtp-to',
              type=str,
              envvar='DBALERT_SMTP_TO',
              callback=validate_smtp)
@click.option('--smtp-server',
              type=str,
              envvar='DBALERT_SMTP_SERVER',
              callback=validate_smtp)
@click.option('--smtp-username',
              type=str,
              envvar='DBALERT_SMTP_USERNAME',
              callback=validate_smtp)
@click.option('--smtp-password',
              type=str,
              envvar='DBALERT_SMTP_PASSWORD',
              callback=validate_smtp)
@click.option(
    '--passwords-from-file',
    default=False,
    envvar='DBALERT_PASSWORDSFROMFILE',
    help=
    'If true, password options are interpreted as filepaths from where to read the password itself. This allows to pass passwords e.g. via docker secrets.'
)
def dbalert(
    station_id,
    time_to_station,
    min_delay,
    lookahead,
    smtp_from,
    smtp_to,
    smtp_server,
    smtp_username,
    smtp_password,
    passwords_from_file,
):
  # read smtp password from file
  if smtp_password and passwords_from_file:
    filepath = smtp_password
    assert path.exists(filepath)
    with open(filepath, 'r') as f:
      smtp_password = f.read()

  print(datetime.now())

  text, station = get_text(station_id=station_id,
                           time_to_station=time_to_station,
                           min_delay=min_delay,
                           lookahead=lookahead)
  if len(text) == 0:
    print('No delays.')
    return
  if smtp_server is None:
    # print instead of sending email
    print('\n' + text)
    return

  msg = EmailMessage()
  msg.set_content(text)
  msg['Subject'] = f'Verspätungen in {station}'
  msg['From'] = formataddr(('DB Alert', smtp_from))
  msg['To'] = smtp_to

  # Send the message via our own SMTP server.
  s = smtplib.SMTP_SSL(smtp_server)
  s.login(user=smtp_username, password=smtp_password)
  s.send_message(msg)
  s.quit()
  print('Email sent')


if __name__ == '__main__':
  dbalert()

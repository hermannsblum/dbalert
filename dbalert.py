import requests
from dateutil.parser import parse
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import click
#from joblib import Memory

#memory = Memory('/tmp')

TIMEFORMAT = '%d.%m.%y, %H:%M'


#@memory.cache
def get_data(station_id, lookahead=180):
  r = requests.get(
      f'https://marudor.de/api/iris/v2/abfahrten/8000207?lookahead={lookahead}&lookbehind=0'
  )
  return r.json()


def get_text(station_id, time_to_station, min_delay, lookahead):
  print('Getting station data...')
  d = get_data(station_id, lookahead=lookahead)
  print(f"Checking {len(d['departures'])} departures...")
  out = ""
  for t in d['departures']:
    if t['train']['type'] not in ('IC', 'EC', 'ICE'):
      continue
    if 'arrival' not in t or t['arrival'].get('delay', 0) < min_delay:
      continue
    if t.get('cancelled', False):
      continue
    if 'departure' not in t:
      continue
    scheduled = parse(t['departure']['scheduledTime']).replace(tzinfo=None)
    departure = parse(t['departure']['time']).replace(tzinfo=None)
    if departure < (datetime.now() + timedelta(minutes=time_to_station)):
      continue
    out += f"Zug: {t['train']['name']}\nZiel: {t['destination']}\nAbfahrt gem. Fahrplan {scheduled.strftime(TIMEFORMAT)}\nAbfahrt gem. Realität {departure.strftime(TIMEFORMAT)}\nGleis {t['departure']['platform']}\n\n"
  return out


def validate_smtp(ctx, param, value):
  """Either all or none smtp parameters should be set."""
  if value is None and any(
      k.startswith('smtp') and ctx.params[k] for k in ctx.params):
    raise click.BadOptionUsage(param,
                               "Either all or no SMTP options need to be set.")


@click.command()
@click.option('--station-id',
              default='8000207',
              show_default=True,
              help='station to query for delayed trains')
@click.option(
    '--time-to-station',
    default=30,
    help=
    '[minutes] Time it takes from user to the station. Only trains with an estimated departure at least this time ahead will be considered.'
)
@click.option(
    '--min-delay',
    default=60,
    help='[minutes] Only trains with at least this delay will be considered')
@click.option(
    '--lookahead',
    default=180,
    help=
    '[minutes] Considers all trains regularly departing in the next X minutes.')
@click.option('--smtp-from', type=str, callback=validate_smtp)
@click.option('--smtp-to', type=str, callback=validate_smtp)
@click.option('--smtp-server', type=str, callback=validate_smtp)
@click.option('--smtp-username', type=str, callback=validate_smtp)
@click.option('--smtp-password', type=str, callback=validate_smtp)
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
):

  text = get_text(station_id=station_id,
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
  msg.set_content(ctx.obj['text'])
  msg['Subject'] = f'Verspätungen in Köln Hbf'
  msg['From'] = smtp_from
  msg['To'] = smtp_to

  # Send the message via our own SMTP server.
  s = smtplib.SMTP_SSL(smtp_server)
  s.login(user=smtp_username, password=smtp_password)
  s.send_message(msg)
  s.quit()
  print('Email sent')


if __name__ == '__main__':
  dbalert()

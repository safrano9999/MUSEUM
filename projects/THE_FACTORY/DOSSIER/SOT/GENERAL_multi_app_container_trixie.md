# Multi-App Container mit Caddy-Index und PHP-Admin (Debian Trixie)

## Ziel

Ein einzelner Container auf Basis von **Debian Trixie**, in dem mehrere kleine Dienste laufen, z. B. 5–10 Flask-Apps, die intern jeweils auf eigenen Ports lauschen.

Nach außen soll der Container nur **einen einzigen Port** öffnen, z. B. `80`.

Davor sitzt **Caddy** als Reverse Proxy. Zusätzlich gibt es:

- eine **Indexseite** auf `/`
- dort werden nur die Apps angezeigt, deren Zielport wirklich lauscht
- eine **Admin-Oberfläche** mit Token
- im Admin-Menü kann man einzelne Dienste:
  - starten
  - stoppen
  - neu starten
  - Logs ansehen

Die Routing-Definition bleibt in der **Caddyfile**.  
Ein kleines Python-Skript liest diese Caddyfile aus und erzeugt daraus die Indexseite.

PHP übernimmt das Admin-Panel und die definierten Control-Actions.

---

## Architektur

```text
Client
  -> Container Port 80
     -> Caddy
        -> /             -> statische/generierte Indexseite
        -> /admin        -> PHP-Admin
        -> /A1/*         -> 127.0.0.1:5001
        -> /A2/*         -> 127.0.0.1:5002
        -> /A3/*         -> 127.0.0.1:5003
        -> ...
```

Interne Komponenten im Container:

- **Caddy**
- **PHP-FPM**
- **mehrere Flask-Apps**
- **ein kleines Python-Skript** zum Generieren der Indexseite
- optional ein einfacher Prozessmanager oder definierte Start/Stop-Skripte

---

## Warum diese Aufteilung sinnvoll ist

### Caddy
Macht nur:
- Requests annehmen
- Pfade routen
- statische Dateien ausliefern
- PHP weiterreichen

### Python
Macht nur:
- Caddyfile lesen
- `handle_path` + `reverse_proxy` Einträge erkennen
- prüfen, ob Zielports wirklich offen sind
- daraus `/var/www/html/index.html` erzeugen

### PHP
Macht nur:
- Token-geschütztes Admin-Menü
- Status anzeigen
- feste Start/Stop/Restart-Befehle ausführen
- Logs lesen

### Flask-Apps
Bleiben jeweils getrennt und lauschen intern auf eigenen Ports.

---

## Verzeichnisstruktur

```text
/app
  /apps
    a1.py
    a2.py
    a3.py
  /admin
    index.php
    login.php
    control.php
    logs.php
    apps.php
  /bin
    gen-index.py
    start-a1.sh
    stop-a1.sh
    restart-a1.sh
    start-a2.sh
    stop-a2.sh
    restart-a2.sh
    ...
  /logs
    a1.log
    a2.log
    a3.log

/etc/caddy
  Caddyfile

/etc/php/8.4/fpm/pool.d
  www.conf

/var/www/html
  index.html
  admin/
```

---

## Basisimage

Empfohlen: `debian:trixie`

Begründung:
- modern genug
- saubere Paketbasis
- Caddy, PHP, Python gut installierbar
- für deinen pragmatischen Container-Stil passend

---

## Komponenten im Container

Zu installieren:

- `caddy`
- `php-fpm`
- `php-cli`
- `python3`
- `python3-flask`
- evtl. `procps`
- evtl. `curl`
- evtl. `net-tools`

Optional:
- `supervisor`, wenn du lieber nicht mit PID-Dateien/Shellskripten arbeiten willst

---

## Routing-Prinzip

Beispiel-Caddyfile:

```caddy
:80 {
    root * /var/www/html
    file_server

    php_fastcgi 127.0.0.1:9000

    handle_path /A1/* {
        reverse_proxy 127.0.0.1:5001
    }

    handle_path /A2/* {
        reverse_proxy 127.0.0.1:5002
    }

    handle_path /A3/* {
        reverse_proxy 127.0.0.1:5003
    }

    handle /admin/* {
        root * /var/www/html
        php_fastcgi 127.0.0.1:9000
        file_server
    }
}
```

Wichtig:
- `handle_path` entfernt den Pfadpräfix vor Weitergabe
- Flask-App hinter `/A1/` sieht also intern nur `/...`

---

## Indexseite

Die Indexseite wird **nicht manuell gepflegt**, sondern aus der Caddyfile generiert.

### Logik
Das Python-Skript:

1. liest die `Caddyfile`
2. sucht nach Blöcken wie:
   - `handle_path /A1/*`
   - `reverse_proxy 127.0.0.1:5001`
3. prüft den Zielport
4. nimmt nur laufende Ziele in die HTML-Indexseite auf

### Ergebnis
Auf `/` sieht man nur die aktuell erreichbaren Apps, z. B.:

- A1
- A3
- notes

A2 fehlt, wenn auf `:5002` gerade nichts lauscht.

---

## Python-Skript für die Indexgenerierung

Beispielidee:

- Input: `/etc/caddy/Caddyfile`
- Output: `/var/www/html/index.html`

Es extrahiert Name + Port und prüft per Socket-Verbindung, ob der Port offen ist.

Damit ist die Indexseite immer ein realistischer Snapshot des aktuell laufenden Zustands.

Optional:
- offline Apps grau anzeigen statt skippen
- Ports zusätzlich anzeigen
- letzte Aktualisierung anzeigen

---

## Admin-Menü

### Zugriff
- URL: `/admin`
- dort Token-Eingabe
- bei korrektem Token: Session setzen
- danach Zugriff auf Admin-Funktionen

### Token
Nicht hardcoden.

Empfohlen:
- Umgebungsvariable `ADMIN_TOKEN`
- oder lokale Datei außerhalb des Webroots

### Funktionen
Pro Dienst:

- Start
- Stop
- Restart
- Status
- Log ansehen

---

## PHP-Adminpanel

PHP ist hier okay, weil es nur:

- Formulare rendert
- Token prüft
- feste Aktionen auf definierte Dienste anwendet
- Logs ausliest

### Wichtig
Keine freie Shell-Eingabe.

Also nicht:
- Textfeld „Befehl ausführen“

Sondern nur:
- feste App-Namen
- feste Buttons
- feste erlaubte Aktionen

Beispiel:
- `A1` → start/stop/restart/logs
- `A2` → start/stop/restart/logs

---

## App-Definitionen in PHP

Eine zentrale Datei, z. B. `apps.php`, definiert alle kontrollierbaren Dienste:

```php
<?php
return [
    'A1' => [
        'port' => 5001,
        'start' => '/app/bin/start-a1.sh',
        'stop' => '/app/bin/stop-a1.sh',
        'restart' => '/app/bin/restart-a1.sh',
        'log' => '/app/logs/a1.log',
    ],
    'A2' => [
        'port' => 5002,
        'start' => '/app/bin/start-a2.sh',
        'stop' => '/app/bin/stop-a2.sh',
        'restart' => '/app/bin/restart-a2.sh',
        'log' => '/app/logs/a2.log',
    ],
];
```

Das ist absichtlich simpel und whitelist-basiert.

---

## Prozessverwaltung

Es gibt zwei sinnvolle Wege.

### Variante A: Shellskripte + PID-Dateien
Pragmatisch und leicht.

Pro App:
- `start-a1.sh`
- `stop-a1.sh`
- `restart-a1.sh`

`start-a1.sh` könnte:
- Prozess starten
- PID speichern
- Logs umleiten

`stop-a1.sh` könnte:
- PID lesen
- Prozess sauber beenden

Vorteil:
- simpel
- gut nachvollziehbar

Nachteil:
- etwas mehr Eigenlogik

### Variante B: Supervisor
Sauberer für viele Dienste.

PHP ruft dann nur:
- `supervisorctl start A1`
- `supervisorctl stop A1`
- `supervisorctl restart A1`
- `supervisorctl status`

Vorteil:
- robuster
- weniger PID-Gefrickel

Nachteil:
- extra Schicht

Für deinen beschriebenen Stil ist **Variante A** wahrscheinlich schon ausreichend.

---

## Logging

Pro App Logdateien, z. B.:

- `/app/logs/a1.log`
- `/app/logs/a2.log`

Das Adminpanel zeigt z. B. die letzten 200 Zeilen.

Möglich:
- `tail -n 200`
- oder direkt Datei lesen und kürzen

Wichtig:
- nur feste, vorher definierte Pfade
- keine freien Dateinamen aus Userinput

---

## Startreihenfolge im Container

Sinnvoller Bootablauf:

1. PHP-FPM starten
2. Flask-Apps starten, die direkt aktiv sein sollen
3. kurzes Warten
4. `gen-index.py` laufen lassen
5. Caddy im Vordergrund starten

Beispiel:

```sh
php-fpm8.4
/app/bin/start-a1.sh
/app/bin/start-a2.sh
sleep 1
python3 /app/bin/gen-index.py
exec caddy run --config /etc/caddy/Caddyfile
```

Optional:
- `gen-index.py` regelmäßig per Loop erneut ausführen
- oder nach jeder Start/Stop-Aktion im Adminpanel neu triggern

---

## Empfohlener Ablauf bei Admin-Aktionen

Wenn im Adminpanel jemand `A2 starten` klickt:

1. Token/Session prüfen
2. `A2` ist als erlaubte App bekannt
3. festes Skript `/app/bin/start-a2.sh` ausführen
4. kurz warten
5. `gen-index.py` neu laufen lassen
6. zurück zur Admin-Seite

Dann bleibt `/` immer aktuell.

Dasselbe bei Stop/Restart.

---

## Sicherheit

Das Panel ist mächtig. Deshalb:

### Pflicht
- langes Admin-Token
- Session statt Token in jeder URL
- nur feste Aktionen und feste App-Namen
- keine freie Shell
- keine freien Dateipfade

### Zusätzlich sinnvoll
- nur intern/LAN zugänglich
- oder hinter vorgeschalteter Access-Lösung
- optional IP-Restriktion in Caddy

### Nicht machen
- Shell-Kommandos direkt aus GET/POST übernehmen
- Logs beliebiger Dateien öffnen
- freie Prozessnamen an `pkill` übergeben

---

## Warum kein index.php als Router

Das wäre möglich, aber unsauber.

Der Reverse-Proxy-Teil gehört in **Caddy**, nicht in PHP.  
PHP sollte nicht Requests an Flask-Apps „weiterleiten“, sondern nur UI/Control machen.

Darum:

- **Routing** → Caddy
- **Control Panel** → PHP
- **Index-Generierung** → Python
- **Apps** → Flask

Das ist deutlich sauberer.

---

## Warum diese Lösung gut zu deinem Stil passt

Weil sie:

- nur **einen externen Port** braucht
- mehrere Flask-Apps bündelt
- kein unnötig schweres Framework für das Adminpanel braucht
- mit einem kleinen Python-Helfer die Übersicht automatisch erzeugt
- pragmatisch bleibt
- aber nicht komplett wild wird

Sie ist nicht „perfekt enterprise“, aber für 5–10 kleine Dienste **sehr brauchbar**.

---

## Mögliche Erweiterungen

### 1. Offline-Dienste im Index grau anzeigen
Statt zu skippen:
- Name sichtbar
- aber nicht klickbar

### 2. Status im Adminpanel
- Port offen?
- PID vorhanden?
- Uptime

### 3. Restart All
Ein definierter Button für alle Apps

### 4. Auto-Refresh Logs
JS im Adminpanel für Live-Nachladen

### 5. Healthchecks
Nicht nur Socket offen, sondern HTTP-Check:
- `GET /health`

### 6. Startprofile
Bestimmte Dienste beim Containerstart automatisch hochfahren, andere nur bei Bedarf

---

## Grenzen der Lösung

### 1. Ein Container, mehrere Prozesse
Formal nicht „rein dogmatisch Docker“, aber für deinen Usecase vertretbar.

### 2. Caddyfile-Parsing
Das Python-Skript sollte nur dein bewusst einfaches Muster lesen, nicht beliebige Caddy-Magie.

### 3. Token-only Auth
Für interne Tools okay, öffentlich nur mit zusätzlicher Sicherung.

### 4. Shellskripte
Einfach, aber auf Disziplin angewiesen.

---

## Minimaler Umsetzungsplan

1. Debian-Trixie-Container bauen
2. Caddy installieren
3. PHP-FPM installieren
4. 2 Test-Flask-Apps einbauen
5. Caddyfile mit `/A1`, `/A2`, `/admin`
6. `gen-index.py` schreiben
7. einfache `index.php` mit Token-Login
8. `apps.php` als Allowlist
9. Start/Stop-Skripte
10. Logansicht
11. Index nach Admin-Aktionen neu generieren

Dann später auf 5–10 Apps ausbauen.

---

## Kurzfazit

Das Projekt ist:

- **ein Multi-App-Container**
- mit **Debian Trixie**
- **Caddy** als einheitlichem Eingang
- **mehreren Flask-Diensten** auf internen Ports
- **Python** für die automatische Generierung der Startseite aus der Caddyfile
- **PHP** für das token-geschützte Adminpanel mit Start/Stop/Logs

Das ist für deinen beschriebenen Zweck ein guter, pragmatischer Mittelweg:
- nicht zu starr
- nicht zu magisch
- gut erweiterbar
- und klar genug getrennt.

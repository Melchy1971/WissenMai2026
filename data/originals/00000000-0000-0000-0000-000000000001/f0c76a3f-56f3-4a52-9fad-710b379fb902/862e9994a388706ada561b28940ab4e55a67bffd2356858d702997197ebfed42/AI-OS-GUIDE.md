# Dein eigenes AI Operating System

Die meisten springen den ganzen Tag zwischen zehn Tools und KI-Chats hin und her und fangen jedes Mal bei null an. Ein AI Operating System dreht das um. Es ist ein zentraler Ort, aus dem heraus du arbeitest, mit einem KI-Agenten mittendrin (sei es Claude, Codex, Hermes oder OpenClaw). Es kennt dich und dein Business, ist mit deinen anderen Systemen verbunden, erledigt Aufgaben und lässt Abläufe von selbst laufen. Ungefähr so wie das Betriebssystem auf deinem Handy.

Es setzt sich aus vier Teilen zusammen:

1. **Wissen (Kontext):** Dein zweites Gehirn: die Ordner und Dateien, in denen steht, wer du bist, was dein Business ist und woran du arbeitest. Das Fundament, und genau das baust du dir mit Obsidian auf.
2. **Verbindungen:** Über MCP, CLI oder API kommt Claude an deine anderen Tools und an Live-Daten. Beispiel: Google Workspace. Claude liest und schreibt Mails, legt Termine in den Kalender oder Dateien in Drive ab. So handelt Claude systemübergreifend für dich.
3. **Skills:** Anleitungen für wiederkehrende Arbeitsprozesse, die Claude immer gleich und in deiner Qualität erledigt. Einmal eingerichtet, jederzeit abrufbar.
4. **Routinen**: Abläufe, die von selbst laufen, entweder lokal oder remote. Jeden Morgen eine Recherche oder jeden Freitag eine Wochenübersicht, auch wenn dein PC aus ist.

Und so groß das klingt: Unter der Haube ist das Ganze überraschend simpel. Am Ende des Tages ist dein AI Operating System einfach nur ein Ordner mit Dateien auf deinem Rechner. In diesen Dateien steht alles über dich und dein Business, und Claude hat Zugriff auf diesen Ordner. Du erklärst ihm einmal, was er wissen und tun soll, und ab dann arbeitet er damit. Keine komplizierte Software, keine Plattform, einfach Ordner und Textdateien, die du und Claude gemeinsam pflegen.

Und genau weil es nur ein Ordner ist, bist du an kein bestimmtes Programm gebunden. Denselben Ordner öffnest du dort, wo du am liebsten arbeitest: in Obsidian mit dem Claudian-Plugin, in VS Code mit Claude Code oder direkt im Terminal, oder du wählst ihn einfach in der Claude Desktop App als Projekt aus. Claude hat in allen Fällen Zugriff auf genau diesen einen Ordner, egal von wo aus du ihn nutzt. Es gibt also nicht den einen richtigen Weg. Ob du lieber in Obsidian schreibst, in VS Code arbeitest oder in der Desktop App, ist ganz dir überlassen. Am Ende ist es immer derselbe Ordner mit deinem Wissen, und Claude arbeitet darin.

## Schritt 0: Wissen, bau dir zuerst deinen Ordner mit Obsidian

Das Fundament ist dein Wissen, also deine Ordnerstruktur und deine Dateien. Die baust du dir mit Obsidian auf.

Falls du Obsidian noch nicht kennst, schau dir zuerst mein Obsidian-Video an (Link in der Beschreibung). Dort zeige ich Schritt für Schritt, wie du deine Struktur aufsetzt. Wenn dein Ordner steht, machst du hier weiter.

Eine Datei ist dabei besonders wichtig: deine `CLAUDE.md`. Das sind die Systemanweisungen für Claude, also die Regeln, an die er sich in deinem Vault hält. Da steht zum Beispiel drin, wie du schreibst, wie deine Ordner aufgebaut sind und dass Claude den Vault regelmäßig auf GitHub pushen soll, damit deine Änderungen überall ankommen. Halte diese Datei aktuell und pass sie immer wieder an: Je besser deine `CLAUDE.md` gepflegt ist, desto verlässlicher arbeitet dein ganzes OS. Wie du sie aufsetzt, zeige ich dir ebenfalls im Obsidian-Video.

## Schritt 1: Verbindungen, Claude an deine Tools anbinden

Dein Wissen steht, jetzt geben wir Claude Hände. Über Verbindungen kommt Claude an deine anderen Tools und an Live-Daten: Google Workspace, Microsoft 365, Slack, Notion, was auch immer du nutzt.

Dafür gibt es drei Wege, und du musst nicht wissen, welcher der richtige ist. **MCP** ist eine Art Standard-Stecker, über den sich Tools an Claude andocken. **CLI** sind kleine Kommandozeilen-Tools, die viele Dienste mitbringen. Und manche Dinge bindest du direkt über die **API** an. Klingt technisch, ist aber dein kleinstes Problem, denn das Einrichten übernimmt Claude.

**Du sagst zu Claude:** "Ich will mein Google Workspace anbinden damit du es für mich steuern kannst. Welche Möglichkeiten gibt es dafür?" Claude sucht dir den passenden Weg (für Google Workspace zum Beispiel ein eigenes CLI-Tool, meine Empfehlung), installiert ihn, führt dich durch den Login im Browser und verbindet alles. Selbst wenn du gar nicht weißt, was es da gibt, fragst du einfach, und Claude findet und richtet es ein.

Ab dann ist Claude operativ. Er liest und schreibt deine Mails, legt Termine in den Kalender, packt Dateien in Drive oder zieht sich Zahlen aus einer Tabelle. Und das Beste: Er macht das mit deinem Wissen aus Schritt 0 im Rücken. Claude weiß, wer du bist und wie du arbeitest, und handelt dann in deinem Namen über all deine Systeme hinweg.

## Schritt 2: Skills, Prozesse einmal erklären und immer abrufen

Jetzt kennt Claude dich und deine Tools. Aber du willst ihm nicht jedes Mal von vorne erklären, wie eine bestimmte Aufgabe läuft, und du willst, dass er mehrere Schritte am Stück von alleine erledigt. Genau dafür sind Skills da.

Ein Skill ist eine Anleitung für Claude: eine Datei, in der einmal sauber drinsteht, wie ein bestimmter Prozess abläuft, Schritt für Schritt, in deiner Qualität. Einmal eingerichtet, rufst du ihn immer wieder ab, und Claude macht den ganzen Ablauf von alleine.

Ein Beispiel: ein Skill, der aus einem Meeting-Transkript automatisch eine saubere Zusammenfassung mit den wichtigsten To-dos erstellt, immer im gleichen Format. Du sagst einmal "fass mir das Meeting zusammen" und gibst die Datei mit, und Claude erledigt alle Schritte von selbst. Mehrere Schritte, eine Ansage.

**Du sagst zu Claude:** "Bau mir einen Skill, der aus einem Transkript drei Social-Media-Posts macht." Claude legt den Skill an, und ab dann ist dieser Prozess für immer abrufbar.

Ein wichtiger Tipp dazu: Installier dir einmal den **Skill Creator Skill** von Anthropic. Das ist ein Meta-Skill, der Claude beibringt, wie man gute Skills schreibt, verbessert und testet. Damit werden deine eigenen Skills deutlich besser. Du findest ihn auf skills.sh (dort einfach nach Anthropic suchen) oder direkt im Repo github.com/anthropics/skills. Am einfachsten installierst du ihn, indem du Claude den Link gibst oder schlicht sagst "installier mir den Skill Creator Skill", den Rest macht Claude.

Installier ihn am besten global, also auf User-Ebene, nicht nur in diesem einen Projekt. Der Grund: Du arbeitest vielleicht noch in anderen Ordnern und Projekten, und so ein grundlegender Skill soll überall verfügbar sein, ohne dass du ihn jedes Mal neu installierst. Faustregel: projektspezifische Skills gehören ins Projekt, übergreifend nützliche Skills installierst du global.

Das ist der Punkt, an dem dein OS dir wirklich Arbeit abnimmt. Du automatisierst ganze Prozesse, und zwar ohne dafür extra ein Automatisierungstool wie n8n aufzusetzen. Für deinen Eigengebrauch reicht oft genau das: ein Skill, einmal geschrieben, beliebig oft genutzt.

## Schritt 3: Routinen, Abläufe von selbst laufen lassen

Skills sind stark, aber du musst sie selbst anstoßen. Du gehst in den Chat und sagst "führ das jetzt aus". Oft willst du aber, dass bestimmte Sachen einfach von allein passieren, jeden Morgen, jeden Montag, jeden Freitag. Dafür gibt es Routinen.

Eine Routine ist nichts anderes als ein Zeitplan für eine Aufgabe (im Hintergrund eine sogenannte Cron-Automatisierung, also "mach das immer zu dieser Zeit"). Du legst einmal fest, was wann passieren soll, und es läuft von selbst. Es gibt zwei Sorten, lokal und remote.

**Lokal** ist das Einfache: Die Routine läuft auf deinem Rechner, in deinem Ordner. Zur eingestellten Zeit startet Claude eine Session und tippt sozusagen die Chat-Nachricht für dich ein, als hättest du dich selbst hingesetzt. Der Haken: Dein PC muss dafür an sein.

**Remote** läuft in der Cloud, also auch dann, wenn dein PC aus ist. Das funktioniert über GitHub. Die Idee dahinter: Dein OS liegt als Repository bei GitHub (dazu kommen wir gleich). Zur eingestellten Zeit nimmt Anthropic dieses Repository, klont es in deren Cloud, startet dort eine Session mit deinem Auftrag und schiebt das Ergebnis danach wieder zurück ins Repository. Bei dir landet es, sobald du dir die Änderungen per Git ziehst (oder automatisch, wenn dein Obsidian synchronisiert, siehe weiter unten).

Ein Beispiel: Eine Routine, die dir jeden Montag früh einen kurzen News-Überblick zusammenstellt, kann problemlos remote laufen, ganz ohne dass dein Rechner an ist. Eine Routine, die dagegen eine Datei aus deinem Download-Ordner verarbeitet, muss lokal laufen, weil nur dein Rechner an diese Datei kommt und nicht die Cloud.

Merksatz: Braucht die Routine etwas von deinem Rechner (lokale Dateien, deinen Download-Ordner), dann lokal. Reicht ihr dein Repo plus deine Verbindungen, dann remote.

## Warum ein Server: dein OS von überall nutzen

Damit steht dein OS, und zwar komplett: Wissen, Verbindungen, Skills und Routinen. Bis hierhin liegt aber alles lokal auf deinem PC. Und jetzt kommt die Frage: Was ist, wenn du nicht an deinem Rechner sitzt? Wenn du unterwegs bist, am Laptop weiterarbeiten willst oder schnell vom Handy aus etwas anstoßen möchtest? Und was, wenn Claude sogar Dinge bauen soll, die dauerhaft laufen und von überall erreichbar sind, zum Beispiel eine kleine App?

Die einfachste Antwort wäre: nur GitHub. Du legst dein OS als Repository ab, ziehst es dir auf den Laptop, änderst was, schiebst es zurück, ziehst es auf dem PC wieder. Für reines Hin- und Herschieben von Dateien zwischen deinen Geräten reicht das tatsächlich.

Aber GitHub allein ist nur ein Speicher, kein laufender Computer. Du kannst dort nicht arbeiten, nur Dateien ablegen und holen. Genau da kommt ein eigener kleiner Server ins Spiel, ein VPS (Virtual Private Server), der rund um die Uhr läuft. Der Unterschied:

- **Von überall arbeiten, nicht nur synchronisieren.** Du verbindest dich von der Claude-App am Handy oder von einem fremden Laptop direkt auf deinen Server und arbeitest dort mit deinem vollen Wissen, in einer echten Claude-Session. Nicht nur Dateien ziehen, sondern wirklich arbeiten.
- **Immer an.** Lang laufende Aufgaben und alles, was rund um die Uhr erreichbar sein soll, läuft weiter, auch wenn dein PC aus ist.
- **Dinge bauen, die dort laufen.** Du kannst Claude auf dem Server Apps oder Tools programmieren lassen, die dann direkt dort laufen und von überall erreichbar sind, nicht nur auf deinem Schreibtisch.
- **Ein einziger Ort der Wahrheit.** Alle Geräte greifen auf denselben aktuellen Stand zu, sauber abgeglichen über GitHub im Hintergrund.

Kurz: GitHub ist dein Backup und dein Abgleich, der Server ist dein Arbeitsplatz, der immer steht. Und das Schöne: Du tippst keine Server-Befehle. Du sagst Claude, was du brauchst, und Claude richtet alles ein, einen Schritt nach dem anderen.

## Das Setup, Schritt für Schritt

### Schritt 4: GitHub

Falls du noch keinen GitHub-Account hast, leg dir einen an, das ist kostenlos.

Wozu GitHub: Es ist der zentrale Speicher und dein Backup. Dein Server und alle deine Geräte gleichen sich darüber ab, und solange gesichert wird, ist nichts verloren, selbst wenn der Server mal ausfällt. Damit Claude dein Github verwalten kann sagst du ihm einfach, er soll die Github CLI installieren und dich anmelden.

**Sobald Github steht sagst du Folgendes:** "Leg mein OS als privates GitHub-Repository an." Claude erledigt das von deinem Rechner aus. Deine geheimen Zugangsdaten, also API-Keys, bleiben dabei in einer separaten Datei und wandern niemals ins Repo.

Falls du auf deinem PC noch nicht bei GitHub angemeldet bist, fragt Claude dich beim ersten Mal nach einem kurzen Login (ein Klick im Browser), danach legt er das Repo an.

### Schritt 5: Den Server bei Hostinger bestellen

Jetzt brauchst du einen Server. Ich empfehle dir [Hostinger](https://www.hostg.xyz/SHJRc), da bekommst du für einen sehr guten Preis ordentlich Ressourcen, schon ab etwa 8 Euro im Monat. Ich nutze den KVM2-Plan, der reicht locker für mehrere Anwendungen. Wähl als Standort Deutschland und als Anwendung direkt **Claude Code**, dann ist Claude Code mit einem Klick schon vorinstalliert. Mit dem Code **JULIANIVANOV** sparst du nochmal 10 Prozent auf alle Jahrespläne.

Nach dem Zahlungsvorgang landest du im Server-Dashboard, und Claude Code läuft schon auf deinem Linux-Server. Oben rechts kommst du ins Terminal, aber keine Sorge: Wir machen fast alles bequem über die Claude Desktop App, nicht in der Konsole.

### Schritt 6: Per SSH mit dem Server verbinden

Damit du den Server bequem von deinem Rechner aus steuerst, verbindest du dich per SSH. Das geht direkt in der **Claude Desktop App**: unten auf **SSH**, dann **SSH-Host hinzufügen**. Du brauchst drei Dinge, einen Namen, die Server-Adresse und einen Schlüssel.

- **Server-Adresse:** Die findest du im Hostinger-Dashboard unter **Root-Zugriff**. Kopier die Adresse und füg sie ein, das "ssh" am Anfang lässt du weg, du brauchst nur die Adresse selbst (also `root@deine-IP`).
- **Name:** Gib dem Server einen Namen, zum Beispiel "VPS" (Virtual Private Server).
- **Port:** Lass ihn einfach auf dem Standardwert.
- **Schlüssel:** Das ist dein digitaler Schlüssel statt eines Passworts. Du legst ihn unter **SSH-Schlüssel verwalten** an, dort erstellst du einen neuen. Hostinger zeigt dir den Befehl dafür. Am einfachsten kopierst du den Befehl samt deiner E-Mail und gibst ihn Claude Code mit den Worten "generiere mir einen SSH-Key für meinen Hostinger-Server", den Rest macht Claude. Hast du schon einen Schlüssel, wählst du einfach "Vorhandenen Key nutzen". Claude zeigt dir dann den Schlüssel, du kopierst ihn, fügst ihn ins Feld ein und klickst auf Speichern.

Danach startest du eine neue Session, wählst deinen SSH-Host samt Schlüssel, und schon bist du auf dem Server und steuerst Claude Code von dort aus. Ab jetzt kommst du von jedem Gerät über diesen Schlüssel auf deinen Server.

### Schritt 7: Dein OS auf den Server holen

Claude Code läuft jetzt auf dem Server, kennt dich aber noch nicht, denn dein OS-Ordner liegt ja noch nicht dort. Also holst du ihn drauf, genau wie vorher auf dem PC. Sag Claude (jetzt in der Server-Session): "Installier die GitHub CLI, melde mich an und lad mein OS-Repository hierher." Claude fragt dich dabei vielleicht, wo auf dem Server der Ordner liegen soll. Am einfachsten direkt auf Root-Ebene als erster Unterordner.

Danach wählst du in der Claude Desktop App unter **Remote-Ordner durchsuchen** genau diesen Ordner aus, und ab dann arbeitet Claude Code direkt in deinem OS auf dem Server, mit all deinem Wissen und deinen Skills.

Den meisten Alltag machst du weiter lokal an deinem Hauptrechner. Der Server ist dann da, wenn du unterwegs bist oder von einem anderen Gerät arbeitest, du verbindest dich einfach per SSH wie gerade gezeigt.

**Damit immer alles synchron bleibt:** Trag in deiner `CLAUDE.md` eine einfache Arbeitsregel ein, nämlich dass Claude vor der Arbeit immer ein `git pull` macht (neuesten Stand holen) und nach der Arbeit ein `git push` (Ergebnis zurückschieben). So bleiben PC, Server und Obsidian automatisch auf demselben Stand, egal wo gerade gearbeitet wird.

### Schritt 8: Vom Handy steuern (Remote Control)

Das Schöne am Server: Du kannst Claude Code von überall steuern, sogar vom Handy. Dafür lässt du mit einem Session-Manager namens `tmux` eine Claude-Session dauerhaft auf dem Server laufen, die nicht stirbt, wenn du das Fenster schließt, und sogar Server-Neustarts übersteht. Über die Remote-Control-Funktion meldest du dich dann einfach in der Claude-App am Handy an und steuerst dein OS auf dem Server, ganz ohne VPN und ohne offenen Port. So laufen auch lange Aufgaben (zum Beispiel über das Slash-Goal-Feature oder in einem Loop) einfach weiter, auch wenn du nicht davor sitzt.

Wie du das genau einrichtest, zeige ich dir Schritt für Schritt in meinem Remote-Control-Video (Link in der Beschreibung).

### Schritt 9: Obsidian automatisch synchron halten

Damit dein Obsidian am PC immer automatisch den neuesten Stand zieht, ohne dass du etwas eintippst, installierst du ein Plugin. Geh in Obsidian unten auf **Einstellungen**, dann **externe Erweiterungen**, **Community-Erweiterungen durchsuchen** und such nach **"Git"** (das Plugin von Vinzent03, über drei Millionen Downloads). Installieren, dann **aktivieren**.

Dann gehst du auf die **Optionen** des Plugins und setzt diese vier Sachen:

1. **Auto commit-and-sync interval (minutes):** auf `5`. "Commit-and-sync" heißt committen, pullen und pushen in einem. Damit sichert und synchronisiert Obsidian deinen Vault alle fünf Minuten von selbst.
2. **Auto commit-and-sync after stopping file edits:** einschalten, damit nichts gepusht wird, während du noch tippst.
3. **Auto pull interval (minutes):** auf `5`. So holt Obsidian Änderungen vom Server und deinen anderen Geräten automatisch rein.
4. **Pull on startup:** einschalten. Dann hast du beim Öffnen sofort den neuesten Stand, ohne fünf Minuten zu warten.

Ab dann gleicht sich Obsidian automatisch ab. Schreibt Claude auf dem Server etwas, taucht es kurz darauf in deinem Obsidian auf, und umgekehrt. Praktischer Nebeneffekt: Damit sparst du dir die kostenpflichtige Obsidian-Sync-Funktion (rund 4 Dollar im Monat), denn über GitHub und dieses Plugin ist dein Vault sowieso auf allen Geräten aktuell.

## Geschafft

Das war der ganze Aufbau. Dein OS liegt jetzt nicht mehr nur auf deinem PC, sondern auch auf einem Server, auf den du von jedem Gerät zugreifst: am PC über Claude Desktop, unterwegs über die Claude-App am Handy und als schöne Ansicht in Obsidian. Über GitHub bleibt dabei alles automatisch synchron.

Ab hier baust du dein OS einfach weiter aus, indem du es Claude sagst. Eine neue **Verbindung** zu einem Tool ("richte mir die Anbindung an mein Google Workspace ein"), einen neuen **Skill** ("bau mir einen Skill, der aus einem Transkript drei Posts macht") oder eine **Automatisierung** als Routine. Du sagst, was du brauchst, und dein OS wächst mit dir.

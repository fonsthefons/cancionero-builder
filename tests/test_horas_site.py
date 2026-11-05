import datetime

from importer.horas_site import psalmody, read_hour, slots, song_id, song_title

R, B = '<FONT COLOR="#FF0000">', '<FONT COLOR="#000000">'

PAGE = f"""<html><body><div>size links</div><div id="cuerpo">
{R}LAUDES<BR>INVITATORIO<BR></FONT>
{B}{R}Ant. </FONT>Al Se&ntilde;or, venid.
</FONT>{R}<BR><BR>Salmo 94 INVITACI&Oacute;N<BR></FONT>{B}<BR>Venid, aclamemos.<BR><BR></FONT>
{R}SALMODIA<BR><BR></FONT>
{B}{R}Ant 1. </FONT>Antífona uno.<BR><BR></FONT>
{R}SALMO 62, 2-9 - EL ALMA SEDIENTA<BR></FONT>
{B}<BR>Línea uno,<BR>línea dos.<BR><BR>Línea tres.<BR><BR>
Gloria al Padre.<BR><BR>{R}Ant. </FONT>Antífona uno.<BR><BR>
{R}Ant 2. </FONT>Antífona dos.<BR><BR></FONT>
{R}Cántico: LAS BODAS - Cf. Ap 19,1-2, 5-7<BR></FONT>{B}<BR></FONT>
{R}Se dice con {B}Aleluya</font> intercalados.<BR></FONT>
{B}<BR>Aleluya.<BR>La salvación<BR>(<font color="#FF0000">R.</font> Aleluya)<BR>
{R}R. </FONT> Aleluya, (aleluya).<BR><BR>{R}Ant. </FONT>Antífona dos.<BR><BR></FONT>
{R}LECTURA BREVE Rm 13, 11b<BR></FONT>{B}<BR>Ya es hora.<BR><BR></FONT>
</div></body></html>"""


def test_read_hour_psalmody():
    parts = psalmody(read_hour(PAGE))
    assert [p["heading"] for p in parts] == ["SALMO 62, 2-9 - EL ALMA SEDIENTA", "Cántico: LAS BODAS - Cf. Ap 19,1-2, 5-7"]
    psalm, canticle = parts
    assert psalm["antiphon"] == "Antífona uno."
    assert psalm["text"] == "Línea uno,\nlínea dos.\n\nLínea tres.\n\nGloria al Padre."
    assert canticle["antiphon"] == "Antífona dos."
    assert canticle["notes"] == ["Se dice con Aleluya intercalados."]
    assert canticle["text"] == "Aleluya.\nLa salvación\n(R. Aleluya)\nR. Aleluya, (aleluya)."


def test_invitatorio_is_not_psalmody():
    parts = read_hour(PAGE)
    assert parts[2]["section"] == "INVITATORIO" and parts[2]["antiphon"] == "Al Señor, venid."


def test_titles():
    assert song_title("SALMO 62, 2-9 - EL ALMA SEDIENTA") == "Salmo 62, 2-9"
    assert song_title("Salmo 118, 145-152 TE INVOCO DE TODO CORAZÓN") == "Salmo 118, 145-152"
    assert song_title("Salmo 26 II") == "Salmo 26 II"
    assert song_title("SALMO 18 A - ALABANZA") == "Salmo 18 A"
    assert song_title("Cántico: JUICIO Ap 11, 17-18; 12, 10b-12a") == "Cántico Ap 11, 17-18; 12, 10b-12a"
    assert song_title("Cántico: SÚPLICA Sir. 36, 1-7. 13-16") == "Cántico Sir 36, 1-7. 13-16"
    assert song_title("Cántico: DIOS JUZGARÁ Is 33,13-16") == "Cántico Is 33, 13-16"
    assert song_id("Salmo 86 - HIMNO A JERUSALÉN") == "salmo-086"


def day(date, week, plain=True):
    return {"date": date, "season": "TIEMPO ORDINARIO", "salterio": week,
            "label": "De la Feria. Salterio" if plain else "De la Solemnidad."}


def test_saturday_evening_is_next_sunday():
    sat = day(datetime.date(2026, 10, 24), "I")
    got = slots(sat, day(datetime.date(2026, 10, 25), "II"))
    assert got == [("semana_i/sabado/laudes", "laudes"),
                   ("semana_ii/domingo/primeras_visperas", "visperas"),
                   ("completas/domingo_primeras_completas", "completas")]


def test_evening_skipped_before_a_feast():
    thu = day(datetime.date(2026, 10, 22), "I")
    assert slots(thu, day(datetime.date(2026, 10, 23), None, plain=False)) == [("semana_i/jueves/laudes", "laudes")]

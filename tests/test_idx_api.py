from scraper.idx_api import filter_reply


KEYWORDS = [
    "Prospektus",
    "Pengambilalihan",
    "Negosiasi Pengambilalihan",
    "Penawaran Tender Wajib",
    "Penawaran Tender",
    "Mandatory Tender Offer",
    "MTO",
    "Transaksi Material",
    "Transaksi Afiliasi",
    "Perubahan Kegiatan Usaha",
    "Perjanjian Pengikatan Jual Beli",
    "Perjanjian Jual Beli",
    "PPJB",
    "Hak Memesan Efek",
    "HMETD",
    "CSPA",
    "Kontrak Penting",
]


def make_reply(judul: str = "", perihal: str = "", filenames=None):
    return {
        "pengumuman": {
            "JudulPengumuman": judul,
            "PerihalPengumuman": perihal,
            "NoPengumuman": "",
            "Kode_Emiten": "ABC",
        },
        "attachments": [{"OriginalFilename": f} for f in (filenames or [])],
    }


def test_filter_matches_title():
    r = make_reply(judul="Pengambilalihan saham oleh investor")
    assert filter_reply(r, KEYWORDS)


def test_filter_matches_attachment():
    r = make_reply(filenames=["dokumen_Penawaran_Tender.pdf"])
    assert filter_reply(r, KEYWORDS)


def test_filter_negative():
    r = make_reply(judul="Laporan keuangan tahunan")
    assert not filter_reply(r, KEYWORDS)

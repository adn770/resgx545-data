import pathlib, struct, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE / 'draft'))
import ring_decode as R
FW = pathlib.Path.home() / 'src/resgx545/tools/fwtask'

def page(entries):
    p = bytearray(0x1000)
    for (e, i, pa0, pa1, pa2, t) in entries:
        struct.pack_into('<8I', p, R.BASE + R.STRIDE * e + 32 * i, 1, pa0, pa1, pa2, t, 0, 0, 0)
    return bytes(p)

def test_decode_orders_by_timer():
    pg = page([(0, 0, 2, 0x02000000, 0x01061a70, 1000), (1, 0, 0x100, 0, 0, 900), (0, 1, 2, 0x02000000, 0x01061a60, 800)])
    ev = R.events(pg)
    assert [x['slot'] for x in ev if x['entry'] == 0] == [0, 1]
    # timer counts down: the larger value is earlier
    assert [x['timer'] for x in R.merged(pg)] == [1000, 900, 800]

def test_torn_slot_is_flagged():
    p = bytearray(page([]))
    struct.pack_into('<I', p, R.BASE + 4, 5)      # pa0 written, flag still 0
    assert R.events(bytes(p))[0].get('torn')

def test_generator_is_deterministic_and_verifies():
    with tempfile.TemporaryDirectory() as d:
        a = pathlib.Path(d) / 'a.s'
        subprocess.run([sys.executable, '-B', str(HERE / 'gen/gen_ring.py'), str(a)], check=True)
        assert a.read_text() == (HERE / 'draft/events_ring.s').read_text()
        text = a.read_text()
        assert ' str ' not in text and 'ldr r8, #81' in text    # no register write; only CR_TIMER (81) is read
        r = subprocess.run([sys.executable, '-B', str(FW / 'fwtask.py'), d, str(a)], capture_output=True, text=True)
        assert r.returncode == 0 and '452 insns' in r.stdout, r.stderr

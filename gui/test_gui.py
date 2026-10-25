"""GUI contracts; injected child failures use no physical driver."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,main
from unittest.mock import patch
from copy import deepcopy
import json,subprocess,sys,time
from gui.server import Jobs,validate_config
from shared.params import load_config

class GuiContracts(TestCase):
    def test_geometry_error_identifies_affected_element(self):
        c=load_config();c['lattice']['elements'][4]['z_start']+=.001
        with self.assertRaisesRegex(ValueError,'gap.*expected'):validate_config(c)
    def test_invalid_numerical_inputs_rejected(self):
        for section,key,value in [('beam','energy_keV',float('nan')),('beam','n_particles',1.2),('output','step_size_m',0),('random','seed',4294967295),('space_charge','mesh',[63,2,63])]:
            with self.subTest(key=key):
                c=load_config();c[section][key]=value
                with self.assertRaises(ValueError):validate_config(c)
    def test_normalization_is_not_input_mutation(self):
        c=load_config();c['space_charge']['mesh']=[63.,63.,63.];old=deepcopy(c)
        out,_=validate_config(c);self.assertEqual(c,old);self.assertIsInstance(out['space_charge']['mesh'][0],int)
    def wait_end(self,m):
        until=time.monotonic()+5
        while time.monotonic()<until:
            j=m.snapshot()
            if j and j[0]['status'] in ('failed','timeout'):return j[0]
            time.sleep(.02)
        self.fail('child did not reach terminal status')
    def test_real_child_failure_and_snapshot(self):
        real=subprocess.Popen
        def spawn(args,**kw):return real([sys.executable,'-c','import sys;print("intentional GUI test failure",flush=True);sys.exit(7)'],**kw)
        with TemporaryDirectory() as tmp,patch('gui.server.subprocess.Popen',side_effect=spawn):
            m=Jobs(tmp,2)
            try:
                c=load_config();j=m.submit(c,['AG'])[0];c['beam']['energy_keV']=999
                end=self.wait_end(m);self.assertEqual(end['status'],'failed');self.assertEqual(end['exit_code'],7)
                saved=json.loads((Path(tmp)/j['id']/'config.json').read_text());self.assertEqual(saved['beam']['energy_keV'],100)
                self.assertFalse((Path(tmp)/j['id']/'result.json').exists())
            finally:m.shutdown()
    def test_real_child_timeout(self):
        real=subprocess.Popen
        def spawn(args,**kw):return real([sys.executable,'-c','import time;time.sleep(10)'],**kw)
        with TemporaryDirectory() as tmp,patch('gui.server.subprocess.Popen',side_effect=spawn):
            m=Jobs(tmp,.15)
            try:m.submit(load_config(),['AG']);self.assertEqual(self.wait_end(m)['status'],'timeout')
            finally:m.shutdown()
    def test_restart_does_not_rerun_interrupted_job(self):
        with TemporaryDirectory() as tmp:
            d=Path(tmp)/('a'*32);d.mkdir();(d/'job.json').write_text(json.dumps({'id':'a'*32,'status':'running','route':'AG','created':0}))
            m=Jobs(tmp)
            try:self.assertEqual(m.snapshot()[0]['status'],'interrupted');self.assertIsNone(m.process)
            finally:m.shutdown()
if __name__=='__main__':main()

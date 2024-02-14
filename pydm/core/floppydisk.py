from pathlib import Path
import shutil
import json

import numpy as np

# ============================================================================
class FloppyDisk:
    def __init__(self,  root_dir, name=None):
        if name is None:
            self.load_default(root_dir)
            self.name = "None"
        else:
            self.path = root_dir / Path(f"DISKS/{name}")
            self.name = name

        self.sound_dir = self.path / "samples"
        self.config = self.load_config()

    def load_default(self, root_dir):
        '''Copy defaults to temp dir'''
        source = root_dir / Path("assets/defaults")
        self.path = root_dir / Path("assets/temp/default")
        shutil.copytree(source, self.path, dirs_exist_ok=True)

    def copy_disk(self, disk_name):
        '''Copy source (current disk) to destination path'''
        source = self.path
        dest = self.dm.ROOT_DIR / Path(f"DISKS/{disk_name}")
        shutil.copytree(source, dest)

    def load_config(self):
        with open(self.path / 'config.json', 'r') as f:
            params = json.load(f)
        return params

    def save_config(self):
        with open(self.path / 'config.json', 'w') as f:
            json.dump(self.config, f, indent=2)
        return

    def load_seqs(self):
        '''Need allow_pickle since array of arrays, which are "objects"'''
        seq_path = self.path / 'sequences.npy'
        return np.load(seq_path, allow_pickle=True)

    def save_seq(self, seqs):
        '''Save sequnces in an array of arrays'''
        np.save(self.path / 'sequences.npy', seqs)
        return

# -*- mode: python ; coding: utf-8 -*-
block_cipher = None


a = Analysis(['dr.py'],
             pathex=['C:\\Users\\Sam\\devel\\drpy'],
             datas=[],
             hookspath=[],
             runtime_hooks=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False,
	     binaries=[('assets/ffmpeg.exe', 'assets'), ('assets/libwinpthread-1.dll', 'assets'), ('assets/tag.dll', '.')],
	     hiddenimports=['plyer.platforms.win.filechooser'],
	     excludes=['numpy'],
	     )
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='dr',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )

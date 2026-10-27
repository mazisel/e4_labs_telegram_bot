import cv2, numpy as np

img = cv2.imread('/w/temp/kapak_tam.png')
W, H = 1848, 2616
img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)
L = 0.114 * img[..., 0] + 0.587 * img[..., 1] + 0.299 * img[..., 2]
sx = W / 924.0

Y, X = np.mgrid[0:H, 0:W]
X9, Y9 = X / sx, Y / sx  # 924 birimli koordinat

# S'nin kesin disinda kalan bolgeler (924x1308 uzayinda)
disinda = (X9 < 345) | (Y9 < 205) | (Y9 > 1125) | ((X9 > 560) & (Y9 < 215))
# metin/rozet/hap bolgelerini disla (sadece arka plan kalsin); parlak pikseller zaten aykiri
def basis(x, y, deg=3):
    return np.stack([x**i * y**j for i in range(deg + 1) for j in range(deg + 1 - i)], 1)

step = 6
idx = disinda[::step, ::step]
xs = (X[::step, ::step][idx]) / W; ys = (Y[::step, ::step][idx]) / H
vals = L[::step, ::step][idx]
A = basis(xs, ys)
keep = np.ones_like(vals, bool)
for _ in range(10):
    c, *_ = np.linalg.lstsq(A[keep], vals[keep], rcond=None)
    keep = np.abs(vals - A @ c) < 3
print('arka plan ornek sayisi', keep.sum(), 'rms', np.sqrt(np.mean((vals[keep] - A[keep] @ c) ** 2)))

bg = (basis((X / W).ravel(), (Y / H).ravel()) @ c).reshape(H, W)
r = (L - bg) / np.maximum(255 - bg, 1)

def ornek(x9, y9):
    return float(np.median(r[int(y9 * sx) - 8:int(y9 * sx) + 8, int(x9 * sx) - 8:int(x9 * sx) + 8]))
print('S ici ornekler', ornek(700, 1000), ornek(800, 300), ornek(450, 520), ' dis', ornek(200, 900), ornek(600, 150))


rs = cv2.resize(r, (924, 1308), interpolation=cv2.INTER_AREA)
metin = cv2.dilate((rs > 0.30).astype(np.uint8), np.ones((9, 9), np.uint8))
r8 = np.clip((rs + 0.05) / 0.3 * 255, 0, 255).astype(np.uint8)
dolu = cv2.inpaint(r8, metin * 255, 12, cv2.INPAINT_TELEA)
# hap butonlari: dikdortgenlerini sil (S ucu aradaki bosluktan gecer)
for (x0, y0, x1, y1) in [(86, 1005, 254, 1060), (263, 1005, 430, 1060), (438, 1005, 605, 1060), (612, 1005, 838, 1060), (86, 1070, 254, 1123)]:
    dolu[y0:y1, x0:x1] = 42
mask = (dolu > 93).astype(np.uint8) * 255
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
print('bilesenler', [int(a) for a in st[1:, cv2.CC_STAT_AREA]])
mask = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 8000]).astype(np.uint8) * 255
cv2.fillPoly(mask, [np.array([[447, 1000], [410, 1100], [612, 1000]], np.int32)], 255)  # hap butonunun sildigi alt uc
big = cv2.resize(mask, (1848, 2616), interpolation=cv2.INTER_LINEAR)
big = (big > 127).astype(np.uint8) * 255
cs, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cs = [c for c in cs if cv2.contourArea(c) > 20000]

def pürüzsüz(pts, sigma=18, pencere=14, aci_esik=55):
    """Koseleri koruyup aradaki egrileri yumusatir. pts: (N,2) yogun kontur."""
    n = len(pts)
    P = pts.astype(np.float64)
    # donus acisi (+-pencere noktalik komsuluk)
    GERCEK = [(889, 231), (830, 412), (700, 674), (609, 649), (923, 642), (923, 783), (410, 1100), (475, 915)]
    idx = []
    for gx, gy in GERCEK:
        d2 = ((P / 2 - np.array([gx, gy])) ** 2).sum(1)
        j = int(d2.argmin())
        if d2[j] < 14 ** 2: idx.append(j)
    idx = sorted(set(idx))
    print('kose', [(int(P[i][0] / 2), int(P[i][1] / 2)) for i in idx])
    if not idx: return P
    out = []
    for a_, b_ in zip(idx, idx[1:] + [idx[0] + n]):
        seg = np.array([P[i % n] for i in range(a_, b_ + 1)])
        m = len(seg)
        if m < 6: out.append(seg[:-1]); continue
        k = np.arange(-3 * sigma, 3 * sigma + 1); w = np.exp(-k**2 / (2 * sigma**2)); w /= w.sum()
        pad = 3 * sigma
        # uclarda nokta yansimasi: ucu sabit tutar
        on = 2 * seg[0] - seg[1:pad + 1][::-1][-min(pad, m - 1):] if m > 1 else seg[:0]
        sn = 2 * seg[-1] - seg[-pad - 1:-1][::-1][:min(pad, m - 1)]
        ext = np.vstack([on, seg, sn])
        sm = np.stack([np.convolve(ext[:, c], w, mode='same') for c in (0, 1)], 1)[len(on):len(on) + m]
        sm[0], sm[-1] = seg[0], seg[-1]
        out.append(sm[:-1])
    return np.vstack(out)

paths = []; prev = cv2.resize(img.astype(np.uint8), (924, 1308))
for cnt in cs:
    dens = pürüzsüz(cnt[:, 0, :])
    ap = cv2.approxPolyDP(dens.astype(np.float32).reshape(-1, 1, 2), 0.8, True)[:, 0, :] * 0.5
    paths.append('M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in ap) + ' Z')
    cv2.polylines(prev, [ap.astype(np.int32)], True, (0, 255, 255), 2)
print('kontur', len(cs), 'nokta', sum(p.count('L') for p in paths))
open('/w/temp/s_path.txt', 'w').write(' '.join(paths))
cv2.imwrite('/w/temp/s_onizleme.png', prev)

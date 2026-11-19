#!/usr/bin/env python3
from pathlib import Path
import sys
r=Path(sys.argv[1]); base=r/'on-tv/android/app/src/main/java/dev/couchtv/ontv'
def change(path,old,new):
 s=path.read_text()
 if s.count(old)!=1: raise RuntimeError(f'{path}: anchor count {s.count(old)} for {old[:60]!r}')
 path.write_text(s.replace(old,new,1))
fire=base/'FireHome.kt'
home=base/'HomeActivity.kt'
state="""
    private const val VISIT_PREFS = "custom_amazon_home"
    @Volatile private var amazonVisitPaused = false
    private fun paused(): Boolean {
        if (amazonVisitPaused) return true
        val p = App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE)
        if (!p.getBoolean("paused", false)) return false
        val oldBoot = p.getInt("boot_count", -1)
        val boot = runCatching { android.provider.Settings.Global.getInt(App.instance.contentResolver, "boot_count", -1) }.getOrDefault(-1)
        val oldEpoch = p.getLong("boot_epoch_ms", -1L)
        val epoch = System.currentTimeMillis() - android.os.SystemClock.elapsedRealtime()
        if ((oldBoot >= 0 && boot >= 0 && oldBoot != boot) ||
            (oldEpoch >= 0 && kotlin.math.abs(epoch-oldEpoch)>120000L)) {
            p.edit().clear().apply()
            return false
        }
        return true
    }
    fun pauseForAmazonVisit() {
        val boot = runCatching { android.provider.Settings.Global.getInt(App.instance.contentResolver, "boot_count", -1) }.getOrDefault(-1)
        App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE).edit()
            .putBoolean("paused", true).putInt("boot_count", boot)
            .putLong("boot_epoch_ms", System.currentTimeMillis()-android.os.SystemClock.elapsedRealtime()).commit()
        amazonVisitPaused = true
        recheck.removeCallbacks(again)
    }
    fun resumeFromAmazonVisit() {
        amazonVisitPaused = false
        App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE).edit().clear().apply()
        poke()
    }
"""
change(fire,'    @Volatile private var lastJump = 0L','    @Volatile private var lastJump = 0L\n'+state)
change(fire,'get() = isFireTv && App.homeEnabled(App.instance)','get() = isFireTv && App.homeEnabled(App.instance) && !paused()')
change(fire,'if (App.homeEnabled(App.instance) && cls in homeClasses) jump(force = true)','if (!paused() && App.homeEnabled(App.instance) && cls in homeClasses) jump(force = true)')
change(fire,'private fun jump(force: Boolean = false) {','private fun jump(force: Boolean = false) {\n        if (paused()) return')
change(home,'override fun onResume() { super.onResume(); front = true;','override fun onResume() { super.onResume(); FireHome.resumeFromAmazonVisit(); front = true;')
bridge="""
        @JavascriptInterface fun openAmazonHome(): Boolean {
            if (!FireHome.isFireTv) return false
            val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .setPackage(FireHome.AMAZON_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if (packageManager.resolveActivity(intent, 0) == null) return false
            main.post {
                FireHome.pauseForAmazonVisit()
                try { startActivity(intent) }
                catch (e: Exception) { FireHome.resumeFromAmazonVisit() }
            }
            return true
        }
"""
change(home,'    inner class Native {','    inner class Native {\n'+bridge)
index=r/'tv-home/web/index.html'
html=index.read_text()
if 'id="custom-amazon-home"' not in html:
    button = """
<style>
#custom-amazon-home { position:fixed; bottom:24px; right:24px; z-index:999999;
 background:#222c3d; color:white; border:2px solid #9bb2d4; border-radius:16px;
 padding:14px 22px; font-size:20px; font-family:Arial,sans-serif; cursor:pointer }
#custom-amazon-home:focus { outline:4px solid white }
</style>
<button id="custom-amazon-home" onclick="if(window.TVOS && TVOS.openAmazonHome){if(!TVOS.openAmazonHome())alert('Amazon Home is not available on this TV')}else alert('Amazon Home is unavailable')">Amazon Home</button>
"""
    if '</body>' not in html: raise RuntimeError('Missing body')
    index.write_text(html.replace('</body>',button+'\n</body>',1))
app=r/'tv-home/web/app.js'
js=app.read_text()
clock_anchor='function clock() {\n    var d = new Date(),'
if clock_anchor in js:
    js=js.replace(clock_anchor,'function clock() {\n    var d = new Date(Date.now() + 3600000),',1)
elif 'function clock() {\n    var d = new Date(Date.now() + 3600000),' not in js:
    raise RuntimeError('Clock offset anchor not found')
app.write_text(js)
print('Native, clock and Amazon Home UI patches applied')

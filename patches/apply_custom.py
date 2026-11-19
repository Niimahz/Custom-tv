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
# Amazon Home belongs in the native, remote-focusable app grid, not in a fixed HTML button.
# The original Settings > People editor is retained; it already supports add/rename/remove.
app=r/'tv-home/web/app.js'
js=app.read_text()
clock_anchor='function clock() {\n    var d = new Date(),'
if clock_anchor in js:
    js=js.replace(clock_anchor,'function clock() {\n    var d = new Date(Date.now() + 3600000),',1)
elif 'function clock() {\n    var d = new Date(Date.now() + 3600000),' not in js:
    raise RuntimeError('Clock offset anchor not found')
app.write_text(js)

# Inject a first-class, focusable app tile into the existing grid.
# Use an inline SVG banner so the icon works offline and scales like other app tiles.
native_anchor='''    return list.map(function (a) {
      return { kind: "app", name: RENAME[a.package] ? t(RENAME[a.package]) : a.label, package: a.package,
        banner: TV.bannerUrl ? TV.bannerUrl(a.package) : "http://tvos.invalid/banner/" + a.package };   // the launcher makes one when the app has none
    });'''
native_replacement='''    var items = list.map(function (a) {
      return { kind: "app", name: RENAME[a.package] ? t(RENAME[a.package]) : a.label, package: a.package,
        banner: TV.bannerUrl ? TV.bannerUrl(a.package) : "http://tvos.invalid/banner/" + a.package };   // the launcher makes one when the app has none
    });
    if (TV && TV.openAmazonHome) items.push({
      kind: "app", name: "Amazon Home", package: "custom.amazon.home",
      banner: "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#2d384c"/><stop offset="1" stop-color="#101826"/></linearGradient></defs><rect width="128" height="128" rx="26" fill="url(#g)"/><path d="M30 65 64 36l34 29v33H75V76H53v22H30Z" fill="#fff"/><path d="M43 106q21 11 43 0" fill="none" stroke="#ffb454" stroke-width="6" stroke-linecap="round"/></svg>')
    });
    return items;'''
if js.count(native_anchor)!=1: raise RuntimeError('Native app list anchor missing or changed')
js=js.replace(native_anchor,native_replacement,1)
launch_anchor='''    opened(a.package);
    if (TV && TV.launch(a.package)) return;
    api("POST", "/api/launch", { app: a.id || a.package })'''
launch_replacement='''    if (a.package === "custom.amazon.home") {
      if (!TV || !TV.openAmazonHome || !TV.openAmazonHome()) flash("Amazon Home unavailable");
      return;
    }
    opened(a.package);
    if (TV && TV.launch(a.package)) return;
    api("POST", "/api/launch", { app: a.id || a.package })'''
if js.count(launch_anchor)!=1: raise RuntimeError('App activation anchor missing or changed')
js=js.replace(launch_anchor,launch_replacement,1)
app.write_text(js)
print('Native, clock, profile settings preserved, and focusable Amazon Home app tile applied')

# Every second: put players in the team of their chestplate (only when it changed, so no spam)

# no chestplate (or an elytra)
execute as @a[team=!mcs_white] unless items entity @s armor.chest #armorcolors:chestplates run team join mcs_white @s

# with a trim: the color of the trim material
execute as @a[team=!mcs_light_purple] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:amethyst"}] run team join mcs_light_purple @s
execute as @a[team=!mcs_red] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:copper"}] run team join mcs_red @s
execute as @a[team=!mcs_aqua] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:diamond"}] run team join mcs_aqua @s
execute as @a[team=!mcs_green] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:emerald"}] run team join mcs_green @s
execute as @a[team=!mcs_yellow] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:gold"}] run team join mcs_yellow @s
execute as @a[team=!mcs_gray] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:iron"}] run team join mcs_gray @s
execute as @a[team=!mcs_blue] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:lapis"}] run team join mcs_blue @s
execute as @a[team=!mcs_dark_purple] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:netherite"}] run team join mcs_dark_purple @s
execute as @a[team=!mcs_white] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:quartz"}] run team join mcs_white @s
execute as @a[team=!mcs_dark_red] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:redstone"}] run team join mcs_dark_red @s
execute as @a[team=!mcs_gold] if items entity @s armor.chest *[minecraft:trim~{material:"minecraft:resin"}] run team join mcs_gold @s

# without a trim: the color of the material
execute as @a[team=!mcs_gold] if items entity @s armor.chest minecraft:leather_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_gold @s
execute as @a[team=!mcs_red] if items entity @s armor.chest minecraft:copper_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_red @s
execute as @a[team=!mcs_dark_gray] if items entity @s armor.chest minecraft:chainmail_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_dark_gray @s
execute as @a[team=!mcs_gray] if items entity @s armor.chest minecraft:iron_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_gray @s
execute as @a[team=!mcs_yellow] if items entity @s armor.chest minecraft:golden_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_yellow @s
execute as @a[team=!mcs_aqua] if items entity @s armor.chest minecraft:diamond_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_aqua @s
execute as @a[team=!mcs_dark_purple] if items entity @s armor.chest minecraft:netherite_chestplate unless items entity @s armor.chest *[minecraft:trim] run team join mcs_dark_purple @s

schedule function armorcolors:check 20t replace

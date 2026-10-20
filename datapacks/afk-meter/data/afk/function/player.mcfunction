# Active = turned the camera, moved, fought, opened a chest, crafted, fished, ... in the last second
scoreboard players set #act afk_tmp 0
execute store result score @s afk_ny run data get entity @s Rotation[0] 10
execute store result score @s afk_np run data get entity @s Rotation[1] 10
execute unless score @s afk_ny = @s afk_yaw run scoreboard players set #act afk_tmp 1
execute unless score @s afk_np = @s afk_pitch run scoreboard players set #act afk_tmp 1
scoreboard players operation @s afk_yaw = @s afk_ny
scoreboard players operation @s afk_pitch = @s afk_np
execute if score @s afk_m1 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m1 0
execute if score @s afk_m2 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m2 0
execute if score @s afk_m3 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m3 0
execute if score @s afk_m4 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m4 0
execute if score @s afk_m5 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m5 0
execute if score @s afk_m6 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m6 0
execute if score @s afk_m7 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m7 0
execute if score @s afk_m8 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m8 0
execute if score @s afk_m9 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m9 0
execute if score @s afk_m10 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m10 0
execute if score @s afk_m11 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m11 0
execute if score @s afk_m12 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m12 0
execute if score @s afk_m13 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m13 0
execute if score @s afk_m14 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m14 0
execute if score @s afk_m15 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m15 0
execute if score @s afk_m16 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m16 0
execute if score @s afk_m17 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m17 0
execute if score @s afk_m18 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m18 0
execute if score @s afk_m19 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m19 0
execute if score @s afk_m20 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m20 0
execute if score @s afk_m21 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m21 0
execute if score @s afk_m22 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m22 0
execute if score @s afk_m23 matches 1.. run scoreboard players set #act afk_tmp 1
scoreboard players set @s afk_m23 0

# After 300 s (5 min) without activity it counts as AFK, including those 5 minutes
execute if score #act afk_tmp matches 1 run scoreboard players set @s afk_idle 0
execute if score #act afk_tmp matches 0 run scoreboard players add @s afk_idle 1
execute if score @s afk_idle matches ..299 run scoreboard players add @s afk_active 1
execute if score @s afk_idle matches 300 run scoreboard players remove @s afk_active 299
execute if score @s afk_idle matches 300 run scoreboard players add @s afk_total 300
execute if score @s afk_idle matches 301.. run scoreboard players add @s afk_total 1

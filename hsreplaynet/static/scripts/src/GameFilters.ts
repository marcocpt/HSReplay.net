import {GameReplay} from './interfaces';
import {BnetGameType, FormatType} from "./hearthstone";

export function nameMatch(game: GameReplay, name: string): boolean {
	return game.global_game.players.some(player => {
		let pName = player.name.toLowerCase();
		if (pName.indexOf(name) !== -1) {
			return true;
		}
		if (name == '"' + pName + '"') {
			return true;
		}
		return false;
	});
}

export function modeMatch(game: GameReplay, mode: string): boolean {
	switch (mode) {
		case "arena":
			return game.global_game.game_type == BnetGameType.BGT_ARENA;
		case "ranked":
			return game.global_game.game_type == BnetGameType.BGT_RANKED_STANDARD
				|| game.global_game.game_type == BnetGameType.BGT_RANKED_WILD;
		case "casual":
			return game.global_game.game_type == BnetGameType.BGT_CASUAL_STANDARD
				|| game.global_game.game_type == BnetGameType.BGT_CASUAL_WILD;
		case "brawl":
			return game.global_game.game_type == BnetGameType.BGT_TAVERNBRAWL_1P_VERSUS_AI
				|| game.global_game.game_type == BnetGameType.BGT_TAVERNBRAWL_2P_COOP
				|| game.global_game.game_type == BnetGameType.BGT_TAVERNBRAWL_PVP;
		case "friendly":
			return game.global_game.game_type == BnetGameType.BGT_FRIENDS;
		case "adventure":
			return game.global_game.game_type == BnetGameType.BGT_VS_AI;
		default:
			return true;
	}
}

export function formatMatch(game: GameReplay, format: string, mode: string): boolean {
	if (!(!mode || mode == "ranked" || mode == "casual")) {
		return true;
	}
	switch(format) {
		case "standard":
			return game.global_game.format == FormatType.FT_STANDARD;
		case "wild":
			return game.global_game.format == FormatType.FT_WILD;
		default:
			return true;
	}
}

export function resultMatch(game: GameReplay, result: string): boolean {
	switch(result) {
		case "won":
			return game.won;
		case "lost":
			return !game.won;
		default:
			return true;
	}
}

export function heroMatch(game: GameReplay, hero: string): boolean {
	let id = game.global_game.players.find(p => p.player_id == game.friendly_player_id).hero_id;
	return getHero(id) == hero;
}

export function opponentMatch(game: GameReplay, hero: string): boolean {
	let id = game.global_game.players.find(p => p.player_id != game.friendly_player_id).hero_id;
	return getHero(id) == hero;
}

//This should be a dictionary
function getHero(heroId: string): string {
	if(heroId.indexOf("HERO_01") !== -1) {
		return "warrior";
	}
	if(heroId.indexOf("HERO_02") !== -1) {
		return "shaman";
	}
	if(heroId.indexOf("HERO_03") !== -1) {
		return "rogue";
	}
	if(heroId.indexOf("HERO_04") !== -1) {
		return "paladin";
	}
	if(heroId.indexOf("HERO_05") !== -1) {
		return "hunter";
	}
	if(heroId.indexOf("HERO_06") !== -1) {
		return "druid";
	}
	if(heroId.indexOf("HERO_07") !== -1) {
		return "warlock";
	}
	if(heroId.indexOf("HERO_08") !== -1) {
		return "mage";
	}
	if(heroId.indexOf("HERO_09") !== -1) {
		return "priest";
	}
}

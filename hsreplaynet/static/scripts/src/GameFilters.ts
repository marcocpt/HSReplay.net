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

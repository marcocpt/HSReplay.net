import * as React from "react";

interface GameHistoryHeroFilterProps extends React.ClassAttributes<GameHistoryHeroFilterState > {
	setQuery: (type: string) => void;
	selected: string;
	default: string;
}

interface GameHistoryHeroFilterState {
}

export default class GameHistoryHeroFilter extends React.Component<GameHistoryHeroFilterProps, GameHistoryHeroFilterState> {

	render(): JSX.Element {
		if (!this.props.selected) {
			this.props.selected = "";
		}
		return (
			<div>
				<select className="form-control" onChange={(e: any) => this.props.setQuery(e.target.value)} value={this.props.selected}>
					<option value="">{this.props.default}</option>
					<option value="druid">Druid</option>
					<option value="hunter">Hunter</option>
					<option value="mage">Mage</option>
					<option value="paladin">Paladin</option>
					<option value="priest">Priest</option>
					<option value="rogue">Rogue</option>
					<option value="shaman">Shaman</option>
					<option value="warlock">Warlock</option>
					<option value="warrior">Warrior</option>
				</select>
			</div>
		);
	}
}

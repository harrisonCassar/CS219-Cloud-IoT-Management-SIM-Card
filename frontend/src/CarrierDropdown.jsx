import React,{ useState, useEffect } from 'react';

const CarrierSwitch = () => {
  const [currentCarrier, setCurrentCarrier] = useState('');
  const [carrierSwitchStatus, setCarrierSwitchStatus] = useState('');
  const carrierSwitchChoices = ['AT&T', 'T-Mobile', 'Verizon', 'Disconnect'];

  const handleCarrierChange = (event) => {
    setCurrentCarrier(event.target.value);
  };

  const handleCarrierSwitch = () => {
    // Perform validation and extract new carrier from the form
    const newCarrier = currentCarrier;
    const request_string = "http://localhost:5000/carrier_switch?carrier=" + newCarrier
      fetch(request_string)
      .then(response => console.log(response)
      /*.json()
      .then(data => {
        console.log(data)
        console.log('here')
      })*/
    )
  };

  return (
    <div>
      <select value={currentCarrier} onChange={handleCarrierChange}>
        <option value="">Select a carrier</option>
        {carrierSwitchChoices.map(carrier => (
          <option key={carrier} value={carrier}>
            {carrier}
          </option>
        ))}
      </select>
      <button onClick={handleCarrierSwitch}>Perform Carrier Switch</button>
    </div>
  );
};

export default CarrierSwitch;